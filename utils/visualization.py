def bool_utf8_symbol(b: bool) -> str:
	"""
	Computes the correspondent UTF-8 symbol representation for a boolean value.
	Where '\u2713' representing True, and '\u2715' represents False.
	:param b: Boolean value.
	:return: UTF-8 character.
	"""
	return '\u2713' if b else '\u2715'