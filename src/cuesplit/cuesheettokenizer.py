# -*- coding: utf-8

import re


class CueSheetTokenizer:

	token_pattern = re.compile(r'([^"\s]+|"[^"]*")(?: +|$)')


	def __init__(self, readline):
		self.readline = readline
		self.line_count = 0
		self.line = None


	def next_line(self):
		line = None
		while not line:
			self.line_count += 1
			line = self.readline()
			if line:
				line = self.tokenize(line)
				if line is None:
					raise ValueError('Line {:d}: Syntax error'.format(self.line_count))
			else:
				line = None
				break

		self.line = line
		return line


	def assert_token_count(self, count):
		if not self.line:
			raise ValueError('Line {:d}: No command found'.format(self.line_count))

		if isinstance(count, int):
			if len(self.line) != count:
				raise ValueError(
					'Line {:d}: Command {!r} requires exactly {:d} parameters'
					.format(self.line_count, self.line[0], count - 1))

		elif isinstance(count, slice):
			start = count.start
			if start is None:
				start = 0
			end = count.end
			if end is None:
				end = float('inf')
			step = count.step
			if step is None:
				step = 1
			else:
				assert step > 0
			if (len(self.line) < start or len(self.line) >= end
				or (step is not None and len(self.line) - start % step)
			):
				raise ValueError(
					'Line {:d}: Command {!r} requires between [{:d}, {}) % {:d} '
						'parameters'
						.format(self.line_count, self.line[0], start - 1, end - 1, step))

		else:
			raise TypeError('count: ' + str(type(count)))


	@classmethod
	def tokenize(cls, s):
		s = s.strip()
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
			match = cls.token_pattern.match(s, p)
			if not match:
				return None
			token = match.group(1)
			if token.startswith('"'):
				assert token.endswith('"')
				token = token[1:-1]
				assert '"' not in token
			tokens.append(token)
			p = match.end()

		return tokens
