# Copyright: 2005 Brian Harring <ferringb@gmail.com>
# License: GPL2

"""
exceptions thrown by repository classes.

Need to extend the usage a bit further still.
"""

class TreeCorruption(Exception):
	def __init__(self, err):
		self.err = err
	def __str__(self):
		return "unexpected tree corruption: %s" % str(self.err)

class InitializationError(TreeCorruption):
	def __str__(self):
		return "initialization failed: %s" % str(self.err)
