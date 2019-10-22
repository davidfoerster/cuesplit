# -*- coding: utf-8

import re


class CueSheetTokenizer:

	token_pattern = re.compile('([^"\\s]+|"[^"]*")(?: +|$)')


	def __init__(self, readline):
		self.readline = readline
		self.line_count = 0
		self.line = None


	def next_line(self):
		line = ''
		while not line and line is not None:
			self.line_count += 1
			line = self.readline()
			if line:
				line = self.tokenize(line.strip())
				if line is None:
					raise ValueError('Line {}: Syntax error'.format(self.line_count))
			else:
				line = None

		self.line = line
		return line


	def assert_token_count(self, count):
		if not self.line:
			raise ValueError('Line {}: No command found'.format(self.line_count))
		if count >= 0:
			if len(self.line) != count:
				raise ValueError(
					'Line {}: Command "{}" requires exactly {} parameters'
					.format(self.line_count, self.line[0], count - 1))
		elif len(self.line) < -count:
			raise ValueError(
				'Line {}: Command "{}" requires at least {} parameters'
				.format(self.line_count, self.line[0], -1 - count))


	@classmethod
	def tokenize(clazz, s):
		if not s:
			return ()

		tokens = []

		# match first
		p = s.find(' ')
		if p >= 0:
			tokens.append(s[:p])
			p += 1
		else:
			tokens.append(s)
			p = len(s)

		# match others
		while p < len(s):
			match = clazz.token_pattern.match(s, p)
			if not match:
				return None
			token = match.group(1)
			if token.startswith('"'):
				token = token[1:-1]
			tokens.append(token)
			p = match.end()

		return tokens
