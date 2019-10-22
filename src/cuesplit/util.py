# -*- coding: utf-8

import itertools
import re
import io
import sys
import os.path
import codecs


FFMPEG = ('ffmpeg',)


def str_maketrans(_from, to, delete=''):
	m = dict(zip(
		map(ord, _from),
		itertools.chain(map(ord, to), itertools.repeat(ord(to[-1])))))
	for c in delete:
		m[ord(c)] = None
	return str.maketrans(m)


def escape_format(s):
	return re.sub(r"[{}]", r"\g<0>\g<0>", s)


def ensure_type(obj, _type):
	if not isinstance(obj, _type):
		obj = _type(obj)
	return obj


def parse_number_with_magnitude(s, number_type=float):
	factor = parse_number_with_magnitude.chars.get(s[-1], 1) if s else 1
	if factor != 1:
		s = s[:-1].rstrip()
	return number_type(s) * factor

parse_number_with_magnitude.chars = dict(zip(
	'yzafpnμmkMGTPEZY', map((10).__pow__, filter(bool, range(-24, 25, 3)))))
parse_number_with_magnitude.chars['u'] = parse_number_with_magnitude.chars['μ']


def ask_input(message, choices=None, default_choice='', ignore_case=True,
	**kwargs
):
	message = [message]
	if choices:
		if isinstance(choices, str):
			message.append('[' + choices + ']')
			choices = choices.casefold()
		else:
			message.append('[' + ', '.join(choices) + ']')
			choices = tuple(map(str.casefold, choices))

	def matches_input_choice(choices, chosen):
		if not isinstance(choices, str) or (chosen and choices):
			return chosen in choices
		else:
			return choices is None or chosen == choices

	chosen = None
	while chosen is None or not matches_input_choice(choices, chosen):
		print(*message, **kwargs)
		chosen = input() or default_choice
		if ignore_case:
			chosen = chosen.casefold()
	return chosen


def make_parent_dirs(path, **kwargs):
	dirname = os.path.dirname(path)
	if dirname:
		os.makedirs(os.path.abspath(dirname), **kwargs)


def detect_bom(bytes):
	if len(bytes) >= 2:
		for bom in BOM_ENCODING_MAP:
			if bytes.startswith(bom):
				return bom
	return b''

BOM_ENCODING_MAP = {
		codecs.BOM_UTF8: 'utf-8-sig',
		codecs.BOM_UTF16_LE: 'utf-16',
		codecs.BOM_UTF16_BE: 'utf-16',
		codecs.BOM_UTF32_LE: 'utf-32',
		codecs.BOM_UTF32_BE: 'utf-32',
	}


def equals_encoding(a, b):
	return a.casefold() == b.casefold() or codecs.lookup(a) == codecs.lookup(b)


def open_read(path, encoding=None):
	if path == '-':
		if encoding and equals_encoding(encoding, sys.stdin.encoding):
			return sys.stdin
		raw = sys.stdin.buffer
	else:
		if encoding:
			return open(path, 'r', -1, encoding)
		raw = open(path, 'rb')

	if not encoding:
		if not raw.seekable():
			with raw:
				bytes = raw.readall()
			raw = io.BytesIO(bytes)
		try:
			bom = detect_bom(raw.read(4))
			raw.seek(0)
		except ex:
			raw.close()
			raise ex
		if bom:
			encoding = BOM_ENCODING_MAP[bom]

	if (encoding and raw is sys.stdin.buffer and
		equals_encoding(encoding, sys.stdin.encoding)
	):
		return sys.stdin
	try:
		return io.TextIOWrapper(raw, encoding)
	except ex:
		raw.close()
		raise ex
