import os
import sys

from .formatter import Formatter, Hint

class Output:
    """A chunk of data to write out.

    The OutputStream class uses this for buffering up data chunks that make up a
    formatted line, deciding when/whether to intersperse additional line breaks.
    """
    def __init__(self, data, formatter):
        self.data = data
        self.formatter = formatter


class OutputStream:
    """An indenting, column-aware, line-buffered, line-wrapping,
    trailing-whitespace-stripping output stream wrapper.
    """
    MAX_LINE_LEN = 80 # Column at which we consider wrapping.
    MIN_LINE_ITEMS = 5 # Required items on a line to consider wrapping.
    TAB_SIZE = 8 # How many visible characters we chalk up for a tab.
    SPACE_INDENT = 4 # When wrapping, add this many spaces onto tab-indentation.

    def __init__(self, ostream):
        """OutputStream constructor. The ostream argument is a file-like object."""
        self._ostream = ostream
        self._col = 0 # 0-based column the next character goes into.
        self._tab_indent = 0 # Number of tabs indented in current line

        # Series of Output objects that makes up a formatted but unbroken line.
        self._linebuffer = []

        # Whether to tuck on space-alignments independently of our own linebreak
        # logic. (Some formatters request this.) These alignments don't
        # currently align properly to a particular character in the previous
        # line; they just add a few spaces.
        self._space_align = False

    def set_space_align(self, enable):
        self._space_align = enable

    def write(self, data, formatter):
        for chunk in data.splitlines(keepends=True):
            if chunk.endswith(Formatter.NL):
                # Remove any trailing whitespace
                chunk = chunk.rstrip() + Formatter.NL

            # For troubleshooting received hinting
            # print_error('XXX "%s" %s' % (chunk, formatter.hints))

            # To disable linewraps, use this instead of the below:
            # self._write(chunk)
            # self._col += len(chunk)
            # if chunk.endswith(Formatter.NL):
            #     self._col = 0
            # continue

            self._linebuffer.append(Output(chunk, formatter))
            self._col += len(chunk)

            if chunk.endswith(Formatter.NL):
                self._flush_line()

    def write_tab_indent(self, formatter):
        self._tab_indent = formatter.indent
        self.write(b'\t' * self._tab_indent, formatter)

    def write_space_align(self, formatter):
        if self._space_align:
            self.write(b' ' * 4 * self._space_align, formatter)

    def get_column(self):
        return self._col

    def _flush_line(self):
        """Helper that flushes out the built-up line buffer.

        This iterates over the Output objects in self._linebuffer, deciding
        whether to write them out right away or in to-be-done batches, possibly
        after newlines, depending on line-breaking hints present in the
        formatter objects linked from the Output instances.
        """
        col_flushed = 0 # Column up to which we've currently written a line
        tbd = [] # Outputs to be done
        tbd_len = 0 # Length of the to-be-done output (in characters)
        line_items = 0 # Number of items (tokens, not whitespace) on formatted line
        using_break_hints = False # Whether we've used advisory linebreak hints yet

        def flush_tbd():
            nonlocal tbd, tbd_len, col_flushed
            for tbd_out in tbd:
                self._write(tbd_out.data)
                col_flushed += len(tbd_out.data)
            tbd = []
            tbd_len = 0

        def write_linebreak():
            nonlocal tbd, tbd_len, col_flushed
            self._write(Formatter.NL)
            self._write(b'\t' * self._tab_indent)
            self._write(b' ' * self.SPACE_INDENT)
            col_flushed = self._tab_indent * self.TAB_SIZE + self.SPACE_INDENT

            # Remove any pure whitespace from the beginning of the
            # continuation of the line we just broke:
            while tbd and not tbd[0].data.strip():
                tbd_len -= len(tbd.pop(0).data)

        def all_blank(tbd):
            return all([len(out.data.strip()) == 0 for out in tbd])

        for out in self._linebuffer:
            if out.data.strip():
                line_items += 1

        # Iterate through the line in pairs of the current and next data chunk
        for out, out_next in zip(self._linebuffer, self._linebuffer[1:] + [None]):
            tbd.append(out)
            # Establish how long the pending chunk is, given hinting:
            if Hint.ZERO_WIDTH not in out.formatter.hints:
                tbd_len += len(out.data)

            # Don't write mid-line whitespace right away: if content follows
            # it that gets wrapped, we'd produce trailing whitespace. We instead
            # push such whitespace onto the next line, where write_linebreak()
            # suppresses it when needed.
            if not out.data.strip():
                continue

            # Honor hinted linebreak suppression around this chunk.
            if Hint.NO_LB_AFTER in out.formatter.hints:
                continue
            if out_next is not None and Hint.NO_LB_BEFORE in out_next.formatter.hints:
                continue
            if Hint.NO_LB_BEFORE in out.formatter.hints and all_blank(tbd[:-1]):
                # Tricky: this catches the case where the preceeding TBD is all
                # whitespace, the current chunk hints NO_LB_BEFORE, _and_ it
                # would trigger line-length violation below.
                continue

            # If the line is too long and this chunk says it best follows a
            # break, then break now. This helps align e.g. multi-part boolean
            # conditionals.
            if Hint.GOOD_AFTER_LB in out.formatter.hints and self._col > self.MAX_LINE_LEN:
                write_linebreak()
                using_break_hints = True

            # When we exceed max line length while flushing a formatted line,
            # break it, possibly repeatedly. But:
            #
            # - If we've used the GOOD_AFTER_LB hint rely exclusively on it for
            #   breaks, because a mix tends to look messy.
            #
            # - If there are only very few items on the line to begin with,
            #   don't bother: it too looks messy.
            #
            elif (not using_break_hints
                  and col_flushed + tbd_len > self.MAX_LINE_LEN
                  and line_items >= self.MIN_LINE_ITEMS):
                write_linebreak()

            flush_tbd()

        # Another flush to finish any leftovers
        flush_tbd()

        self._linebuffer = []
        self._col = 0

    def _write(self, data):
        try:
            if self._ostream == sys.stdout:
                # Clunky: must write string here, not bytes. We could
                # use _ostream.buffer -- not sure how portable that is.
                self._ostream.write(data.decode('UTF-8'))
            else:
                self._ostream.write(data)
        except BrokenPipeError:
            #  https://docs.python.org/3/library/signal.html#note-on-sigpipe:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            sys.exit(1)


def print_error(*args, **kwargs):
    """A print() wrapper that writes to stderr."""
    print(*args, file=sys.stderr, **kwargs)
