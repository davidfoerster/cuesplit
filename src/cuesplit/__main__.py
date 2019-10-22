# -*- coding: utf-8

import sys
import os
import os.path
import locale
import argparse
import collections.abc
import cuesplit
from .cuesheet import CueSheet
from .cuetrack import CueTrack
from . import util
from .util import FFMPEG


def _get_filename_format(args):
	prefix = 'format:'
	if args.filename_format.startswith(prefix):
		filename_format = args.filename_format[len(prefix):]
	else:
		filename_format = (
			CueTrack.FILENAME_FORMAT_TEMPLATES.get(args.filename_format))
		if filename_format is None:
			raise ValueError('Unknown format: ' + repr(args.filename_format))

	if args.extension:
		filename_format += os.extsep + util.escape_format(args.extension)
	if args.filename_prefix:
		filename_format = os.path.join(
			util.escape_format(args.filename_prefix), filename_format)

	return filename_format


COMMON_SAMPLE_RATES = {
		8000, 11025, 16000, 22050, 32000, 37800, 44100, 48000, 64000, 88200,
		96000, 176400, 192000,
	}

def _set_sample_rate(args):
	if args.sample_rate is not None:
		if isinstance(args.sample_rate, float) and args.sample_rate.is_integer():
			args.sample_rate = int(args.sample_rate)
		if args.sample_rate not in COMMON_SAMPLE_RATES:
			reply = util.ask_input(
				'WARNING: You specifyed an uncommon sampling rate of {} Hz. Do you really want to proceed?'
					.format(locale.format('%' + type(args.sample_rate).__name__[0],
						args.sample_rate, True)),
				'yN', 'n', True, 'tty', end=' ', file=sys.stderr)
			if reply.upper() != 'Y':
				sys.exit('Aborted by user request')

		args.ffmpeg_args += (
			'-filter:a', 'aresample=resampler=soxr', '-ar', str(args.sample_rate))


class AppendAndOverrideDefaulAction(argparse.Action):

	def __init__(self, option_strings, dest, **kwargs):
		if 'nargs' in kwargs:
			raise ValueError('nargs not allowed')
		super().__init__(option_strings, dest, **kwargs)


	def __call__(self, parser, namespace, value, option_string=None):
		attr = getattr(namespace, self.dest, None)
		if isinstance(attr, collections.abc.MutableSequence):
			attr.append(value)
		else:
			setattr(namespace, self.dest, [value])


def _parse_args(argv):
	parser = argparse.ArgumentParser(description=cuesplit.__doc__)
	parser.add_argument('-c', '--cuesheet', metavar='CUE',
		required=True, help='Path to a cuesheet file')
	parser.add_argument('-x', '--extension', default='wav',
		help='Output file name extension')
	parser.add_argument('-f', '--format', metavar='FMT',
		dest='filename_format', default='short',
		help='Output file name format; either "short", "long", or "full"; '
			'alternatively "format:" followed by a format string. (default: short)')
	parser.add_argument('-F', '--format-filter', metavar='FILTER',
		choices=CueTrack.translate_metadata.maps.keys(), default='full',
		help='Select with which character set to translate filename format '
			'arguments. "full" and "windows" will translate all characters '
			'prohibited in Windows semantics; "minimal" and "posix" will translate '
			'all characters prohibited in POSIX semantics. (default: full)')
	parser.add_argument('-p', '--prefix', metavar='DIR',
		dest='filename_prefix',
		help='Adds a directory prefix to the output file name.')
	p_enc = parser.add_mutually_exclusive_group()
	p_enc.add_argument('-w', '--windows', dest='cuesheet_encoding',
		action='store_const', const='windows-1252',
		help='Set the cuesheet character encoding to Windows-1252')
	p_enc.add_argument('-e', '--cuesheet-encoding', metavar='CHARSET',
		help='Cuesheet character encoding. (default: locale default)')
	parser.add_argument('--ffmpeg-cmd', metavar='EXE',
		action=AppendAndOverrideDefaulAction, default=FFMPEG,
		help='FFmpeg base command; may be specified multiple times for additional '
			'arguments. (default: ffmpeg)')
	parser.add_argument('-v', '--verbose',
		action='count', default=0,
		help='Increase output verbosity.')
	parser.add_argument('-r', '--sample-rate', metavar='FREQ',
		type=util.parse_number_with_magnitude,
		help='Convert the output to a different sampling rate. (default: keep)')
	parser.add_argument('--simulate', '--dry-run', '--no-act',
		action='store_true', default=False,
		help='Only print what would be done.')
	parser.add_argument('ffmpeg_args',
		nargs='*', default=[],
		help='Additional FFmpeg comman-line arguments. You may need to separate '
			'these from cuesplit\'s non-positional command-line arguments with "--" '
			'to avoid confusion.')
	args, unknown_args = parser.parse_known_args(argv)

	if unknown_args:
		parser.error(
			'{1!s}\n\n'
			'Unrecognized command-line arguments: {2:s}.\n\n'
			'If you mean to have these passed to FFmpeg, you should add "--" '
			'between the non-positional and positional arguments. Call '
			'"{0:s} --help" for more usage information.'
				.format(parser.prog, argv, ', '.join(map(repr, unknown_args))))

	CueTrack.translate_metadata.map = (
		CueTrack.translate_metadata.maps[args.format_filter])

	args.filename_format = _get_filename_format(args)

	cuesheet_dir = os.path.dirname(args.cuesheet) or os.curdir
	cuesheet = CueSheet()
	with util.open_read(args.cuesheet, args.cuesheet_encoding) as src:
		cuesheet.read(src, cuesheet_dir)
	args.cuesheet = cuesheet

	_set_sample_rate(args)

	return args


def run_cmdline(argv=None):
	import locale
	locale.setlocale(locale.LC_ALL, locale.getdefaultlocale())
	args = _parse_args(argv)

	if not args.cuesheet.tracks:
		sys.exit('Error: No tracks to convert!')

	cmd = []
	if args.simulate or args.verbose > 0:
		cmd.append(CueTrack.convert_action_print)
	if not args.simulate:
		cmd.append(CueTrack.convert_action_call)
	cmd += args.ffmpeg_cmd
	args.cuesheet.convert(args.filename_format, cmd, args.ffmpeg_args)


run_cmdline()
