# Copyright: 2005 Brian Harring <ferringb@gmail.com>
# License: GPL2

def pre_curry(func, *args, **kwargs):
	"""passed in args are prefixed, with further args appended"""

	def callit(*moreargs, **morekwargs):
		kw = kwargs.copy()
		kw.update(morekwargs)
		return func(*(args+moreargs), **kw)

	callit.__original__ = func
	return callit

def post_curry(func, *args, **kwargs):
	"""passed in args are appended to any further args supplied"""

	def callit(*moreargs, **morekwargs):
		kw = morekwargs.copy()
		kw.update(kwargs)
		return func(*(moreargs+args), **kw)

	callit.__original__ = func
	return callit

def pretty_docs(wrapped, extradocs=None):
	wrapped.__module__ = wrapped.__original__.__module__	    
	doc = wrapped.__original__.__doc__
	if extradocs is None:
		wrapped.__doc__ = doc
	else:
		wrapped.__doc__ = extradocs
	return wrapped

