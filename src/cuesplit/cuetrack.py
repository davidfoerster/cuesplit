# -*- coding: utf-8

import itertools
import sys
import os.path
import subprocess
from . import util
from .util import FFMPEG


class CueTrack:

	FRAMES_PER_SECOND = 75

	FILENAME_FORMAT_TEMPLATES = {
			'short': '{TRACKNUMBER:02d} {TITLE}',
			'long': '{TRACKNUMBER:02d} {ARTIST} - {TITLE}',
		}
	FILENAME_FORMAT_TEMPLATES['full'] = os.path.join(
	'{ALBUMARTIST}', '[{DATE}] {ALBUM}', FILENAME_FORMAT_TEMPLATES['short'])


	def translate_metadata(self, metadata):
		return {
			k: v.translate(self.translate_metadata.map) if isinstance(v, str) else v
			for k, v in metadata.items()
		}

	translate_metadata.maps = {
			'minimal': util.str_maketrans(
				os.sep + (os.altsep or ''), '-', '\u0000'),
			'full': util.str_maketrans(
				'"<>:/\\|*' + os.sep + (os.altsep or ''), '\'-', '?')
		}
	translate_metadata.maps['full'].update((c, None) for c in range(32))
	translate_metadata.maps['windows'] = translate_metadata.maps['full']
	translate_metadata.maps['posix'] = translate_metadata.maps['minimal']
	translate_metadata.map = translate_metadata.maps['full']


	def __init__(self, index=None, offset=None, length=None, file=None,
		track_type=None, title=None, performer=None
	):
		self.index = index
		self.offset = offset if offset is not None else {}
		self.length = length
		self.file = file
		self.track_type = track_type
		self.title = title
		self.performer = performer


	def parse_offset(self, s, offset_index=1):
		tok = s.split(':', 2)
		if len(tok) != 3:
			raise ValueError('Invalid offset syntax: ' + s)
		minutes, seconds, fragments = map(int, tok)
		self.offset[offset_index] = (
			(minutes * 60 + seconds) * self.FRAMES_PER_SECOND + fragments)


	def get_metadata(self, album_metadata, **kw_album_metadata):
		if album_metadata:
			metadata = album_metadata.copy()
			metadata.update(kw_album_metadata)
		else:
			metadata = kw_album_metadata

		if self.index is not None:
			metadata['TRACKNUMBER'] = self.index
		if self.title:
			metadata['TITLE'] = self.title
		if self.performer:
			metadata['ARTIST'] = self.performer
		elif 'ALBUMARTIST' in metadata:
			metadata['ARTIST'] = metadata['ALBUMARTIST']

		return metadata


	def convert(self, filename_format=FILENAME_FORMAT_TEMPLATES['short'],
		ffmpeg_cmd=FFMPEG, ffmpeg_args=(), album_metadata=None
	):
		cmd = list(itertools.dropwhile(callable, ffmpeg_cmd))
		cmd.append('-ss')
		cmd.append(format(self.offset[1] / self.FRAMES_PER_SECOND, '.3f'))
		cmd.append('-i')
		cmd.append(self.file[0])

		if self.length is not None:
			cmd.append('-t')
			cmd.append(format(self.length / self.FRAMES_PER_SECOND, '.3f'))

		metadata = self.get_metadata(album_metadata)
		cmd += metadata_to_ffmpeg_args(metadata)
		cmd += ffmpeg_args

		filename = filename_format.format(**self.translate_metadata(metadata))
		util.make_parent_dirs(filename, exist_ok=True)
		cmd.append(filename)

		actions = tuple(itertools.takewhile(callable, ffmpeg_cmd))
		if actions:
			for action in actions:
				action(cmd)
		else:
			self.convert_action_call(cmd)


	@staticmethod
	def convert_action_call(cmd):
		subprocess.check_call(cmd, stdin=subprocess.DEVNULL)


	@staticmethod
	def convert_action_print(cmd):
		print('Running:', repr(cmd), end='\n\n', file=sys.stderr)


def metadata_to_ffmpeg_args(metadata):
	args = []
	for k, v in metadata.items():
		args.append('-metadata')
		args.append(k + '=' + str(v))
	return args
