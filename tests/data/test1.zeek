##! A test script with all kinds of formatting errors.
##!
##! This Zeekygen head comment has multiple lines with more detail
##! about this module. It spans two lines.

@load foo/bar/baz.zeek    # A "preprocessor" line with comment
@load  blum/frub

@if(getenv("ZEEK_PORT") != "")
redef Broker::default_port =  to_port(getenv( "ZEEK_PORT"));
@endif

module  Test;
	
  export {
	# A regular comment
	type An::ID: enum {
		## A Zeekygen comment
		ENUM_VAL1, ##< A Zeekygen post-comment
		  ##< that continues on the next line
		## Anoter Zeekygen comment
		PRINTLOG
	};

        ## A constant.
        const a_constant=T  &redef ;

        ## An option.
        option an_option: table[ string,count ] of string=table() &redef;

        ## An function.
	global a_function : function(foo: BAR) :bool;
}

function a_function ( a: int, b: count ) : bool
	{
	if ( foo in bar )
		return somthing [ foo$bar ] (bar) ;
	else
		# A comment
		return T;

	if ( foo in bar )
		{
		return somthing [ foo$bar ] (bar) ;
		}
	else
		{
		# A comment
		return T;
		}

	if ( | foo | > 0 )
		print "foo";
	else if  (bar && baz)
		print "bar";
	else if ( baz)
		print "baz";
	else
		print "or else!";
	}

function blanklines() {

	foo();
	bar();
  
	# With one comment
	baz(); # and another comment

	# String-like directives:
	print @DIR,  @FILENAME;

}


