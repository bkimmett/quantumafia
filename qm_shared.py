#for later - if a NK would kill an entangler, they can't have been the entangler, so mark those universes as contradictory (collapse them).

import random, mmap, os
from sys import exit, stdout
from traceback import print_stack

universe_file = None
player_names = None
player_codewords = None
flip_was_setup = False
can_entangle_results = []

def player_to_pos(letter):
	if letter == '#':
		print("Tried to convert a # (empty slot) to a player ID. This may mean the player action string has an invalid target in it.")
		print_stack(file=stdout)
		exit()
	return ord(letter)-65
	
def pos_to_player(pos):
	return chr(65+pos)
	
def parse_universe(universe):
	return universe.decode('utf-8').rstrip("\n").split(sep="-", maxsplit=1)

def oxford_comma(termlist, lastitem_prefix):
	if len(termlist) == 1:
		return termlist[0]
	elif len(termlist) == 2:
		return f"{termlist[0]} {lastitem_prefix} {termlist[1]}" #"A and B"
	else:
		termlist_2 = termlist[:]
		termlist_2[-1] = f"{lastitem_prefix} {termlist_2[-1]}" #"or Z"
		return ", ".join(termlist_2) #"A, B, C, or Z"

def single_letter(string): #type checker for argparse
	if len(string) > 1 or not string.isalpha() or not string.isascii():
		raise ValueError("Player identifier must be exactly one letter")
	return string.upper()


def precess_rng(seed, day_num, is_day):
	return random.Random(seed+2*day_num+(0 if is_day else 1)) #1 for N0, 2 for D1, 3 for N1, etc., etc.
	

def read_game_info(day_num, is_day):
	#read game info from gameinfo.txt
	global orig_setup, random_source, player_board_order
	
	try:
		with open("gameinfo.txt", 'r') as gameinfo:
			orig_setup_string = gameinfo.readline().rstrip('\n')
			setup_string_list = orig_setup_string.split(sep="-", maxsplit=2)
			#read in game setup vars
			orig_setup = (int(setup_string_list[0]), int(setup_string_list[1]), *[char == '1' for char in setup_string_list[2]]) #tuple - set once
			
			random_source = precess_rng(int(gameinfo.readline().rstrip('\n')), day_num, is_day)
			player_board_order = gameinfo.readline().rstrip('\n') #don't need to split - this will not be modified.
			
			return orig_setup, random_source, player_board_order
			
			
	except OSError:
		print("Couldn't find the game info file, gameinfo.txt. Run initial_setup.py before running this file.")
		exit()
		
def read_current_info(day_num, is_day):
	global universe_file, current_setup, player_liveness, num_universes
	
	get_universe_file(day_num, is_day)
	assert universe_file is not None
	
	universe_file.seek(0)
	current_setup_string = universe_file.readline().decode('utf-8').rstrip('\n')
	setup_string_list = current_setup_string.split(sep="-", maxsplit=2)
	current_setup = [int(setup_string_list[0]), int(setup_string_list[1]), *[char == '1' for char in setup_string_list[2]]] #num players, num mafia, detective, entangler, follower, guard
	player_liveness_string = universe_file.readline().decode('utf-8').rstrip('\n')
	player_liveness = [player_liveness_string[x*2:(x+1)*2] for x in range(orig_setup[0])]
	num_universes = int(universe_file.readline().decode('utf-8').rstrip('\n'))
	universe_file.readline() #skip actions
	return current_setup, player_liveness, num_universes		
		
def read_player_names():
	global orig_setup, player_names
	try:
		with open("players.txt", 'r') as players:
			player_names = [players.readline().rstrip('\n') for _ in range(orig_setup[0])]
			return player_names
		
	except OSError:
		print("Couldn't find the player info file, players.txt. Run initial_setup.py before running this file.")
		exit()

def read_player_codewords():
	global orig_setup, player_codewords
	try:
		with open("codewords.txt", 'r') as codewords:
			player_codewords = [codewords.readline().rstrip('\n') for _ in range(orig_setup[0])]
			return player_codewords
		
	except OSError:
		print("Couldn't find the player codeword file, codewords.txt. Run initial_setup.py before running this file.")
		exit()
	
def get_player_name(player_index, include_marker=False):
	global player_names
	if player_names is None:
		read_player_names()
	return player_names[player_index][0 if include_marker else 3:]
	
def get_player_codeword(player_index):
	#codewords are kind of complicated because we need to figure out where 
	global player_codewords, player_board_order
	if player_codewords is None:
		read_player_codewords()
	codeword_index = player_board_order.index(pos_to_player(player_index))
	return player_codewords[codeword_index]

def get_universe_file(day_num, is_day, switch=False):
	global universe_filedesc, universe_file, universe_file_num, universe_file_is_day #store state
	if universe_file is not None and switch and (universe_file_num != day_num or universe_file_is_day != is_day): #only switch if we want a different file from the one we already have open
		close_universe_file()
	if universe_file is None:
		universe_filedesc = os.open(f"universes-{'D' if is_day else 'N'}{day_num}.txt", os.O_RDONLY)	#NOT the same as regular open()
		universe_file = mmap.mmap(universe_filedesc, 0, access=mmap.ACCESS_READ)
		universe_file_num = day_num
		universe_file_is_day = is_day
	return universe_file	

def close_universe_file():
	global universe_filedesc, universe_file #retrieve state
	assert universe_file is not None
	universe_file.close()
	os.close(universe_filedesc)
	universe_file = None

def get_universe_file_metrics():
	global universe_filedesc, universe_file, universe_line_chars, universe_num_digits, universe_records_start
	assert universe_file is not None
	universe_file.seek(0)		
	universe_file.readline() #skip 4 lines to get to actual universes
	universe_file.readline()
	universe_file.readline()
	universe_file.readline()
	universe_records_start = universe_file.tell()
	single_universe = universe_file.readline().decode('utf-8').rstrip("\n")
	universe_line_chars = len(single_universe) + 1 #include length of newline
	universe_num_digits = len(single_universe.split(sep="-", maxsplit=1)[0])
	
def read_masonry_file(filename):
	with open(filename, 'r') as masonrylist:
		#masonry file format is # lines. 
		#[player 1][player 2]-round generated-[entanglers LEFT]-[entanglers RIGHT]
		#masonry array format is [left player idx, right player idx, round#, [possible left entangler idxes], [possible right entangler idxes]]
		existing_masonries = []
		while True:
			masonry_string = masonrylist.readline().rstrip('\n')
			if len(masonry_string) == 0:
				break #all done!

			masonry_string_list = masonry_string.split(sep="-", maxsplit=3)
			unpacked_masonry = [*(player_to_pos(item) for item in masonry_string_list[0]), int(masonry_string_list[1]), [player_to_pos(item) for item in masonry_string_list[2]], [player_to_pos(item) for item in masonry_string_list[3]]]
			existing_masonries.append(unpacked_masonry)	
		return existing_masonries
	
def write_masonry_file(masonries, filename):
	if not current_setup[3]: #has_entangler_right_now
		return #bail out, no action to take
	try:
		with open(filename, 'x') as masonryfile:
			masonries_strings = ("{}{}-{}-{}-{}".format(
				pos_to_player(masonry[0]), 
				pos_to_player(masonry[1]), 
				masonry[2], 
				"".join(pos_to_player(item) for item in masonry[3]), 
				"".join(pos_to_player(item) for item in masonry[4])) for masonry in masonries)
			write_lines_to_file(masonryfile, masonries_strings)
		
	except FileExistsError:
		print(f"Error - Can't write to the masonries file, {filename} - it already exists.")
		exit()
	#write masonry file
	
def write_universe_file(universes, filename, liveness, setup, actions):
	global universe_num_digits
	universe_format = "{:0"+str(universe_num_digits)+"}-{}"
	try:
		with open(filename, 'x') as output_universes:
			output_universes.write("{}-{}-{}{}{}{}\n{}\n{}\n{}\n".format(
				setup[0], setup[1], 
				*(1 if item else 0 for item in setup[2:]),			
				"".join(liveness), 
				len(universes), #number of universes
				actions
				))
				
			packed_universes = (universe_format.format(universe[0],"".join(universe[1])) for universe in universes)
			write_lines_to_file(output_universes, packed_universes)
	
	except FileExistsError:
		print(f"Error - Can't write to the universe file, {filename} - it already exists.")
		exit()
		#write universe file
		
def write_final_universe_file(universes, filename):
	try:
		with open(filename, 'x') as output_universes:
			packed_universes = ("{}-{}".format(universe[0],"".join(universe[1])) for universe in universes)
			write_lines_to_file(output_universes, packed_universes)
	
	except FileExistsError:
		print(f"Error - Can't write to the final universe file, {filename} - it already exists.")
		exit()
		#write universe file

def write_lines_to_file(file_handle, lines):
	first_line = True
	for line in lines:
		if not first_line:
			file_handle.write("\n"+line)
		else:
			first_line = False
			file_handle.write(line)	
	
def compare_livenesses(universe_buffer, original_liveness):
	current_livenesses = [single_liveness[1] != '#' for single_liveness in original_liveness] #False means indeterminacy. True means either dead in all universes (previously reported) or alive in one or more universes.

	for universe_chunk in universe_buffer:
		for this_idx in (idx for idx, is_determinate in enumerate(current_livenesses) if not is_determinate): #only check if indeterminate players are alive
			if universe_chunk[1][this_idx] not in 'XV': #hooray! They're alive!
				current_livenesses[this_idx] = True			
		if all(current_livenesses): #end early if everyone is still alive somewhere
			break
			
	return current_livenesses
	
def transform_liveness_roles(universe_buffer, incoming_liveness): #this fn updates the roles so that if any player has a specific, guaranteed role, that is listed in the global liveness as a shortcut
	updated_livenesses = incoming_liveness[:] #make a copy
	needs_checking = [item[0] == '#' for item in incoming_liveness] #role
	check_results = [None for item in incoming_liveness]

	for universe_chunk in universe_buffer:
		for this_idx in (idx for idx, check_this_player in enumerate(needs_checking) if check_this_player): #only check players who we're not sure about
			role = universe_chunk[1][this_idx]
			if role in 'ABC':
				role = 'A' #normalize mafia roles
			if role in 'XV': #get original state from dead
				role = get_player_role_in_orig_universe(this_idx, int(universe_chunk[0]))
			if check_results[this_idx] is None: #check if state is not yet seen in any universe
				check_results[this_idx] = role
			elif check_results[this_idx] != role: #...or check if state mismatches the last one we saw. 
				needs_checking[this_idx] = False #this resets to none and disqualifies from further checking.
				check_results[this_idx] = None
		if not any(needs_checking): #end early if everyone who needs checking is indeterminate
			break

	for player_id, state in enumerate(check_results):
		if state is not None:
			assert updated_livenesses[player_id][0] == state or updated_livenesses[player_id][0] == '#'
			updated_livenesses[player_id] = f"{state}{updated_livenesses[player_id][1]}"

	return updated_livenesses

def close_masonries(existing_masonries, current_liveness, universes): #this mutates existing_masonries
	if not current_setup[3]: #has_entangler_right_now
		return #bail out, no action to take
	
	can_entangle = get_can_entangle(current_liveness, universes)
	
	masonries_to_remove = []		
	for idx, masonry in enumerate(existing_masonries):
		if current_liveness[masonry[0]][1] != '#' or current_liveness[masonry[1]][1] != '#':
			#either player dead, close masonry
			print(f"Closing masonry between {get_player_name(masonry[0], include_marker=True)} and {get_player_name(masonry[1], include_marker=True)}, one or more players died.")
			masonries_to_remove.append(idx)
			continue
		masonry[3] = [ent1_candidate for ent1_candidate in masonry[3] if can_entangle[ent1_candidate]]
		masonry[4] = [ent2_candidate for ent2_candidate in masonry[4] if can_entangle[ent2_candidate]]
		if len(masonry[3]) == 0 or len(masonry[4]) == 0:
			print(f"Closing masonry between {get_player_name(masonry[0], include_marker=True)} and {get_player_name(masonry[1], include_marker=True)}, no entanglers for one or more sides.")
			masonries_to_remove.append(idx)
	masonries_to_remove.sort(reverse=True)

	for removing_idx in masonries_to_remove:
		del existing_masonries[removing_idx] #we remove in reverse order else earlier removals will get the indexes wrong for later

def get_can_entangle(liveness, universes):
	global can_entangle_results
	if len(can_entangle_results) > 0:
		return can_entangle_results
	can_entangle_results  = [None if item[1] == '#' and item[0] == '#' else False for item in liveness] #if a single player is fixed as entangler they rather paradoxically can't entangle so...
	#None means indeterminate btw
	for universe in universes:
		entangler_idx = universe[1].index('E')
		if can_entangle_results[entangler_idx] is None:
			can_entangle_results[entangler_idx] = True
			if all(item is not None for item in can_entangle_results):
				break
	for idx, item in enumerate(can_entangle_results):
		if item is None:
			can_entangle_results[idx] = False #if we didn't find an entangler record for this player after scanning all universes, mark it as false
	return can_entangle_results
	
# [S] Cascade.
def cascade(universe_buffer, incoming_player_livenesses, voted_player_id=None): #expects regular liveness format, not t/f
	#this fn takes the universe buffer and pre-calculated liveness state. It determines if anyone is now 100% dead (voted out or NKed), and if so, flips them, comparing with day 1 universe if necessary. We use a classical for loop rather than for..in to allow mutating the universe buffer directly. (This is normally bad practice but I don't have another spare 8 GB of memory.)
	flip_setup()
	current_liveness = incoming_player_livenesses[:]
	
	while len(universe_buffer) > 0: 
		liveness_result = compare_livenesses(universe_buffer, current_liveness)
	
		if all(liveness_result):
			print("Done determining dead players.")
			#success! no one's died (this go-round).
			#flip() will mutate livenesses and we return the mutated liveness list
			return current_liveness #we expect to mutate the buffer rather than 
	
		if voted_player_id is not None and liveness_result[voted_player_id] == False:
			#handle voted-out player first
			print(f'{get_player_name(voted_player_id, include_marker=True)} is now 100% dead (voted out). Flipping...')
			flip(voted_player_id, universe_buffer, current_liveness, True)
			liveness_result[voted_player_id] = True
	
		for player_id in (idx for idx, item in enumerate(liveness_result) if item == False): #for each dead player...
			print(f'{get_player_name(player_id, include_marker=True)} is now 100% dead {"(voted out?)" if player_id == voted_player_id else "(nightkilled)"}. Flipping...')
			flip(player_id, universe_buffer, current_liveness, voted_player_id == player_id)

	if len(universe_buffer) == 0: #SHOULD be impossible, but what do I know?
		paradox("cascade")
	
def flip_setup():
	global flip_was_setup
	if flip_was_setup:
		return
	get_universe_file(1, True, switch=True) #switch to orig universe, we'll need it
	get_universe_file_metrics()
	flip_was_setup = True

def get_player_role_in_orig_universe(player_idx, univ_id): #must call flip_setup first else expect calamity
	global universe_file, universe_line_chars, universe_num_digits, universe_records_start
	universe_file.seek(universe_records_start+univ_id*universe_line_chars+universe_num_digits+1+player_idx)
	return chr(universe_file.read_byte())

def get_probability_table_idx(player_idx):
	global player_board_order
	return player_board_order.index(pos_to_player(player_idx))

def flip(player_id, universe_buffer, current_liveness, is_vote): #will mutate universe_buffer and current_liveness
	global random_source
	
	entangler_seen = False
	entangler_only = True 
	
	nonentangler_universe_ids = []
	
	#in the first pass, we just assess the player's state in the still living universes.
	for universe in universe_buffer:
		universe_id = int(universe[0])
		player_role_in_that_universe = get_player_role_in_orig_universe(player_id, int(universe[0]))
		#print(f"Player is {player_role_in_that_universe} in universe {int(universe[0])}.") #debug
		if player_role_in_that_universe in 'BC':
			player_role_in_that_universe = 'A'

		universe.append(player_role_in_that_universe)
		
		if player_role_in_that_universe == 'E':
			entangler_seen = True
			continue
			
		entangler_only = False
		nonentangler_universe_ids.append(universe_id)

	#now, we pick a flip. There are a few ways to do this depending on if the entangler is present or not
	
	if entangler_only:
		#every possibility is the entangler. Also leads to a non-collapse situation.
		print(f"{get_player_name(player_id)} was the ENTANGLER.")
		assert len(nonentangler_universe_ids) == 0
		print("No universes have collapsed.")
		current_liveness[player_id] = f"E{'V' if is_vote else 'X'}"
		return #no mutation needed, no collapses from this event
	elif entangler_seen:
		#pick a random choice from the combined list of all the non-entangler universes.
		chosen_universe_id = random_source.choice([*town_universe_idxs, *scum_universe_idxs, *det_universe_idxs, *follower_universe_idxs, *guard_universe_idxs])
		print(f"Chosen universe ID = {chosen_universe_id}")
	else:
		#easy way to do it
		#we could probably just do this a few times at the start and it'd serve for most cases, but whatever. we spend an extra rng flip that way
		chosen_universe_id = int(random_source.choice(universe_buffer)[0])
		print(f"Chosen universe ID = {chosen_universe_id}")
	final_player_role = get_player_role_in_orig_universe(player_id, chosen_universe_id)
	
	current_liveness[player_id] = f"{final_player_role}{'V' if is_vote else 'X'}"
	
	if final_player_role == 'T':
		print(f"{get_player_name(player_id)} was TOWN.")

	if final_player_role in 'ABC':
		print(f"{get_player_name(player_id)} was SCUM.")
		final_player_role = 'A' #normalize scum roles for upcoming use in removal
		
	if final_player_role == 'D':
		print(f"{get_player_name(player_id)} was the DETECTIVE.")
		
	if final_player_role == 'F':
		print(f"{get_player_name(player_id)} was the FOLLOWER.")

	if final_player_role == 'G':
		print(f"{get_player_name(player_id)} was the GUARD.")
	
	universes_before = len(universe_buffer)
	
	print(f"About to collapse universes...")
	#we have an interesting problem here: we can't actually use 'del' to delete all these universes. Not really. Each 'del' is an O(n) operation. It'll take forever.
	#instead, we write over the list using a list comprehension, and strip off the temporary data we wrote to each universe.
		
	universe_buffer[:] = [universe[0:2] for universe in universe_buffer if universe[2] == final_player_role]  #this may take a very long time. up to 30 minutes for D1
	
	universes_after = len(universe_buffer)
	
	print(f"{universes_before - universes_after} universes collapse.")
		
	if len(universe_buffer) == 0:
		#this should be impossible, but we check anyway
		paradox(f"flip of {get_player_name(player_id, include_marker=True)}") #will exit
	
def check_scum_victory(universe_buffer, num_scum_left):
	global player_liveness
	indeterminate_universe_found = False
	always_scum = [True for _ in player_liveness]
	sometimes_scum = [False for _ in player_liveness]

	for universe in universe_buffer:
		num_nonscum_players = 0
		for idx, player in enumerate(universe[1]):
			if player in 'ABC':
				sometimes_scum[idx] = True
				continue
			else:
				always_scum[idx] = False
			if player in 'XV': 
				continue
			num_nonscum_players += 1
			if num_nonscum_players >= num_scum_left:
				indeterminate_universe_found = True
				break
		if indeterminate_universe_found:
			break
	
	if not indeterminate_universe_found:
		write_final_universe_file(universe_buffer, "universes-final.txt")
		print("*** SCUM VICTORY ***")
		always_scum_indexes = [idx for idx, item in enumerate(always_scum) if item]
		sometimes_scum_indexes = [idx for idx, item in enumerate(sometimes_scum) if item and not always_scum[idx]]
		print(always_scum_indexes)
		print(sometimes_scum_indexes)
		num_variable_scum = num_scum_left - len(always_scum_indexes)
		always_scum_names = [get_player_name(idx) for idx in always_scum_indexes]
		sometimes_scum_names = [get_player_name(idx) for idx in sometimes_scum_indexes]
		if num_variable_scum == 0:
			print(f'The surviving scum player{"s" if num_scum_left > 1 else ""}, {oxford_comma(always_scum_names, "and")}, {"have" if num_scum_left > 1 else "has"} won.')
		else: #num_variable_scum must be  > 1 
			print(f'The surviving scum player{"s" if num_scum_left > 1 else ""}, {", ".join(always_scum_names)}{" and " if len(always_scum_names) > 0 else ""}{num_variable_scum} of {oxford_comma(sometimes_scum_names, "or")}, {"have" if num_scum_left > 1 else "has"} won.')
		exit()
		
	
def paradox(stage):
	print("*** TIME PARADOX ***")
	print(f"Every universe has collapsed during the {stage} stage. This may indicate an error in the code or an improbable situation.")
	exit()
	

if __name__ == "__main__":
	print("Don't run this file directly. Quantumafia puts some of its shared functions in it.")