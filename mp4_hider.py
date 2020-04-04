# A file to read mp4 file
# This has been minimally tested, but does work with 
# several mp4 files downloaded expressly for this project

import struct
import sys
from os import path

location = 0
infile = ""
chunks = []

def check_header(f, atom_type):
	# Assume the we're encountering the header atom next, if not - quit
	start = f.tell()
	hlen = struct.unpack('>i',f.read(4))[0]
	hid = f.read(4)
	## print("hd_len = {} hd_id = {}".format(hlen, hid))

	if (hid != atom_type):
		exit(-1)

	return (start + hlen)

def find_atom(f, start, atom_type):	
	# Jump past the mvhd atom until we reach a 'trak' atom
	while (True):
		f.seek(start,0)

		# Break out if we've reached the end of the file
		if (f.read(1) == b''):
			break

		f.seek(start,0)
		atom_len = struct.unpack('>i',f.read(4))[0]
		atom_id = f.read(4)
		# print("len = {} id = {}".format(atom_len, atom_id))
		if(atom_id == atom_type):
			break

		start = start + atom_len

	return start

def main():
	global location

	print("Welcome to MP4 file reader.")
	with open(infile, "rb") as f:
		in_bytes = f.read(16)
		print("bytes[4:8] = {}".format(in_bytes[4:8]))
		if in_bytes[4:8] == b'ftyp':
			print("Passed check 1 - ftyp")
		else:
			print("Failed check 1 - ftyp")
			return

		"""
		from [5]:
		* 8+ bytes file type box = long unsigned offset + long ASCII text string 'ftyp'
  			-> 4 bytes major brand = long ASCII text main type string
  			-> 4 bytes major brand version = long unsigned main type revision value
  			-> 4+ bytes compatible brands = list of long ASCII text used technology strings
    			- types are ISO 14496-1 Base Media = isom ; ISO 14496-12 Base Media = iso2
    			- types are ISO 14496-1 vers. 1 = mp41 ; ISO 14496-1 vers. 2 = mp42
    			- types are quicktime movie = 'qt  ' ; JVT AVC = avc1
    			- types are 3G MP4 profile = '3gp' + ASCII value ; 3G Mobile MP4 = mmp4
    			- types are Apple AAC audio w/ iTunes info = 'M4A ' ; AES encrypted audio = 'M4P '
    			- types are Apple audio w/ iTunes position = 'M4B ' ; ISO 14496-12 MPEG-7 meta data = 'mp71'
		"""
		if in_bytes[8:12] == b'mp42' or in_bytes[8:11] == b'mmp4':
			print("Passed check 2 - dealing with mp4")
		else: 
			print("Failed check 2 - dealing with mp4")
			return

		f.seek(location, 0)
		check = f.read(1)
		while check != b'':

			# Seek to the read location and obtain the next 4 bytes
			f.seek(location, 0)
			in_bytes = f.read(4)
			atom_type = f.read(4)

			# Construct an int from the 4 bytes read, that's the section size
			block_len = struct.unpack('>i',in_bytes)[0]

			# Add the block information
			next_loc = location+block_len
			chunks.append({"len": block_len, "start":location, "end": (next_loc - 1), "type":atom_type})
			location = next_loc

			# Set our check to ensure we haven't reached the EOF
			f.seek(location, 0)
			check = f.read(1)

		moov_offset = 0
		# Find the trak atom within the moov atom
		for chunk in chunks:
			if chunk["type"] == b'moov':
				moov_offset = chunk["start"]

		for chunk in chunks:
			if chunk["type"] == b'mdat':
				mdat_offset = chunk["start"]

		f.seek(mdat_offset,0)
		mdat_len_addr = f.tell()
		mdat_len = struct.unpack('>i',f.read(4))[0]

		# Confirm we're dealing with moov
		f.seek(moov_offset, 0)
		moov_len_addr = f.tell()
		moov_len = struct.unpack('>i',f.read(4))[0]
		moov_id = f.read(4)


		# Assume the we're encountering the mvhd atom next, if not - quit
		end_mvhd = check_header(f, b'mvhd')
		# Find the 'trak' part of the 'moov' atom
		trak_start = find_atom(f, end_mvhd, b'trak')

		# Assume the we're encountering the tkhd atom next, if not - quit
		end_tkhd = check_header(f, b'tkhd')
		mdia_start = find_atom(f, end_tkhd, b'mdia')

		# Assume the we're encountering the mdhd atom next, if not - quit
		end_mdhd = check_header(f, b'mdhd')
		minf_start = find_atom(f, end_mdhd, b'minf')

		# Assume the we're encountering the vmhd atom next, if not - quit
		end_vmhd = check_header(f, b'vmhd')
		stbl_start = find_atom(f, end_vmhd, b'stbl')
		print("stbl starts at {}".format(stbl_start,))

		stco_start = find_atom(f, stbl_start+8, b'stco')
		f.seek(stco_start+12, 0)
		num_chunks = struct.unpack('>i',f.read(4))[0]
		chunk_offset_array = f.tell()
		first_offset = struct.unpack('>i',f.read(4))[0]
		print("offset array addr: {}, num_chunks = {}, first offset: {}".format(chunk_offset_array, num_chunks, first_offset))


		## At this point we have all of the content chunk offsets.
		# We should be able to update these offsets to all be
		# increased by the same amount, and hopefully all else will work
		# there may be other offsets that break and corrupt our file, though
		with open(hidefile, 'rb') as hidef:
			with open(outfile, 'wb') as outf:
				
				## We will write everything exactly as it is
				# up until the check offset array:

				f.seek(0,0)

				# Write up to the chunk address array
				outf.write(f.read(chunk_offset_array))

				# Update all offsets to include length of hidden file
				for i in range(0,num_chunks):
					offset = struct.unpack('>i',f.read(4))[0] + hidef_len
					outf.write(struct.pack('>i', offset))
				
				# Write the remainder of the moov section
				curr = f.tell()
				to_read = mdat_offset-curr
				outf.write(f.read(to_read))

				# Update the length of the mdat section
				outf.write(struct.pack('>i',mdat_len + hidef_len))

				# Copy over the mdat section name
				f.seek(4,1)
				outf.write(f.read(4))

				# Write the hidden content into the new
				# padding area that has been created
				outf.write(hidef.read(hidef_len))

				# Write the remainder of the file
				outf.write(f.read(infile_len-f.tell()))

if __name__ == "__main__":
	if len(sys.argv) != 4:
		print("usage 'python mp4_reader.py [carrier filename] [file to hide] [outfile-name]'\n")
	else:
		infile = sys.argv[1]
		infile_len = path.getsize(infile)

		hidefile = sys.argv[2]
		hidef_len = path.getsize(hidefile)
		print("The file to be hidden has size: {} bytes",format(hidef_len))
		
		outfile = sys.argv[3]

		if path.exists(infile) and path.exists(hidefile):
			if path.isfile(infile) and path.isfile(hidefile):
				main()
		else:
			print("No such file")
			exit(1)
	
