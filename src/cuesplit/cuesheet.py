import sys
import os.path
from .cuetrack import CueTrack
from .cuesheettokenizer import CueSheetTokenizer
from .util import FFMPEG


class CueSheet:

	def __init__(self, title=None, performer=None):
		self.title = title
		self.performer = performer
		self.tags = {}
		self.tracks = []


	def get_metadata(self):
		metadata = self.tags.copy()

		if self.title:
			metadata['ALBUM'] = self.title
		if self.performer:
			metadata['ALBUMARTIST'] = self.performer
		if self.tracks:
			metadata['TRACKTOTAL'] = len(self.tracks)

		return metadata


	def read(self, src, directory=os.curdir):
		tok = CueSheetTokenizer(src.readline)

		# read header
		while tok.next_line() is not None:
			if tok.line[0] in ('TITLE', 'PERFORMER'):
				tok.assert_token_count(2)
				setattr(self, tok.line[0].lower(), tok.line[1].strip())
			elif tok.line[0] == 'REM':
				tok.assert_token_count(-2)
				if (len(tok.line) >= 3 and
					tok.line[1] in ('DATE', 'GENRE', 'DISCID', 'COMMENT')
				):
					self.tags[tok.line[1]] = ' '.join(map(str.strip, tok.line[2:]))
				else:
					print(
						'Line {}: Ignoring cuesheet comment:'.format(tok.line_count),
						*tok.line, file=sys.stderr)
			elif tok.line[0]:
				break

		# read tracks
		current_file = None
		current_track = None
		while tok.line:
			if tok.line[0] == 'FILE':
				tok.assert_token_count(3)
				current_file = (os.path.join(directory, tok.line[1]), tok.line[2])
				current_track = None

			elif tok.line[0] == 'TRACK':
				tok.assert_token_count(3)
				if current_file is None:
					raise ValueError(
						'Line {}: No FILE for TRACK command'.format(tok.line_count))
				current_track = CueTrack(
					index=int(tok.line[1]), track_type=tok.line[2], file=current_file)
				if current_track.track_type == 'AUDIO':
					if current_track.file[1] not in ('WAVE', 'MP3'):
						raise ValueError(
							'Line {}: Trying to add an "{}" track but the FILE type "{}" is unsupported.'
							.format(tok.line_count, current_track.track_type,
									current_track.file[1]))

					self.tracks.append(current_track)

			elif tok.line[0] == 'INDEX':
				tok.assert_token_count(3)
				if current_track is None:
					raise ValueError(
						'Line {}: No TRACK for {} command'
							.format(tok.line_count, tok.line[0]))
				current_track.parse_offset(tok.line[2], int(tok.line[1]))

			elif tok.line[0] in ('TITLE', 'PERFORMER'):
				tok.assert_token_count(2)
				if current_track is None:
					raise ValueError(
						'Line {}: No TRACK for {} command'
							.format(tok.line_count, tok.line[0]))
				setattr(current_track, tok.line[0].lower(), tok.line[1].strip())

			elif tok.line[0] == 'REM':
				pass

			elif tok.line[0]:
				print(
					'Line {}: Ignoring illegal command: {}'
						.format(tok.line_count, tok.line[0]),
					file=sys.stderr)

			tok.next_line()


	def compute_lengths(self):
		for i in range(0, len(self.tracks) - 1):
			current_track = self.tracks[i]
			next_track = self.tracks[i + 1]
			if current_track.file == next_track.file:
				next_offset = next_track.offset.get(0)
				if next_offset is None:
					next_offset = next_track.offset[1]
				current_track.length = next_offset - current_track.offset[1]
			else:
				current_track.length = None


	def convert(self, filename_format=CueTrack.FILENAME_FORMAT_TEMPLATES['short'],
		ffmpeg_cmd=FFMPEG, ffmpeg_args=()
	):
		self.compute_lengths()

		album_metadata = self.get_metadata()
		album_metadata['CUESHEET'] = ''

		for track in self.tracks:
			track.convert(
				filename_format, ffmpeg_cmd, ffmpeg_args, album_metadata)
