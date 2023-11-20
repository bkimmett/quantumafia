#!/usr/bin/env python3

import argparse, qm_shared, os, mmap
from sys import exit

masonries_now = None

def tab():
	return "        " #8 spaces

def plural(num):
	return "s" if num != 1 else ""
	
def percent(num, num_universes, square_brackets=False):
	result = num / num_universes
	if (result*100).is_integer():
		if square_brackets:
			return "{:,} [{:.0%}]".format(num, result)
		return "{:,} ({:.0%})".format(num, result)
	else:
		if square_brackets:
			return "{:,} [{:.1%}]".format(num, result)
		return "{:,} ({:.1%})".format(num, result)
	
def table_percent(fraction):
	if (fraction*100).is_integer():
		return "{:<9.0%}".format(fraction) #< is right pad. 5 is min total width. .0 indicates decimal places. % forces percentage calculation
	else:
		return "{:<9.1%}".format(fraction)
	
def and_or_all(counts, terms, include_percents=False, override_total=None):
	total = override_total if override_total is not None else sum(counts)
	list_mix = [(thiscount, terms[idx]) for idx, thiscount in enumerate(counts) if thiscount > 0]
	if len(list_mix) == 1:
		if list_mix[0][1] == 1:
			return f"{list_mix[0][1]} in it" #"
		else:
			return f"{list_mix[0][1]} in all of them" #"the detective in all of them"
	elif len(list_mix) > 1:
		output = ""
		for idx, item in enumerate(list_mix):
			if include_percents:
				block = f"{item[1]} in {percent(item[0], total, square_brackets=True)}"
			else:
				block = f"{item[1]} in {item[0]:,}"
			if idx == len(list_mix) - 1: #last item
				if idx > 1:
					output += ","
				output += " and "
			elif idx > 0: #not first or last item
				output += ", "
			output += block
		return output # "scum in #, the detective in #, and vanilla town in #"
	return "ERROR!"

def read_to_universe_with_id(universe_file, target_id):
	while True:
		line = universe_file.readline()
		if len(line) == 0:
			return None #give up
		universe = qm_shared.parse_universe(line)
		if int(universe[0]) == target_id:
			return universe
		elif int(universe[0]) > target_id:
			print("Warning: Skipped target universe in read-to.")
			return #give up

def read_masonry_differences():
	global args
	global masonries_then, masonries_now
	#use same decode format from night.py
	masonries_now = qm_shared.read_masonry_file("masonries-{}{}.txt".format("D" if args.daynight == 'day' else "N", args.num))
	if (args.daynight == 'day' and args.num == 1) or (args.daynight == 'night' and args.num == 0): 
		masonries_then = []
	else:
		masonries_then = qm_shared.read_masonry_file("masonries-{}{}.txt".format("N" if args.daynight == 'day' else "D", args.num - 1 if args.daynight == 'day' else args.num ))	
		

def print_masonry_count_diff():
	global masonries_then, masonries_now, args
	if masonries_now is None:
		read_masonry_differences()
	masonries_added = 0
	masonries_removed = 0
	masonries_then_idx = 0
	masonries_now_idx = 0
	while masonries_then_idx < len(masonries_then) and masonries_now_idx < len(masonries_now):
		round_number_comparison = masonries_then[masonries_then_idx][2] - masonries_now[masonries_now_idx][2]
		player_check = masonries_then[masonries_then_idx][0] == masonries_now[masonries_now_idx][0] and masonries_then[masonries_then_idx][1] == masonries_now[masonries_now_idx][1]
			
		if round_number_comparison == 0 and player_check:
			#these masonries are equal. Nothing has changed here.
			masonries_then_idx += 1
			masonries_now_idx += 1
		else:
			#the 'then' masonry is older - it's closed. (Because the masonry lists are in sorted order, and any added must be at the end, and we're not at the end yet.
			masonries_removed += 1
			masonries_then_idx += 1
	if masonries_then_idx < len(masonries_then):
		masonries_removed += len(masonries_then) - masonries_then_idx
	if masonries_now_idx < len(masonries_now):
		masonries_added += len(masonries_now) - masonries_now_idx
	if args.daynight == 'day':
		print(f'Last night, {"no" if masonries_added == 0 else masonries_added} {"masonries were" if masonries_added != 1 else "masonry was"} created, and {"no" if masonries_removed == 0 else masonries_removed} {"masonries" if masonries_removed != 1 else "masonry"} closed.')
	else:
		print(f'Today, {"no" if masonries_removed == 0 else masonries_removed} {"masonries" if masonries_removed != 1 else "masonry"} closed.')
		if masonries_added > 0:
			print("WARNING: Some masonries were added during day phase? This makes no sense.")

def print_masonry_differences(player_idx, liveness_now, liveness_then):
	global masonries_then, masonries_now, args
	if masonries_now is None:
		read_masonry_differences()
	has_printed_anything = False
	#masonry array format is [left player idx, right player idx, round#, [possible left entangler idxes], [possible right entangler idxes]]
	#masonry arrays will be ordered, as well.
	masonries_then_subset = [masonry for masonry in masonries_then if masonry[0] == player_idx or masonry[1] == player_idx]
	masonries_now_subset = [masonry for masonry in masonries_now if masonry[0] == player_idx or masonry[1] == player_idx]
	masonries_then_idx = 0
	masonries_now_idx = 0
	#we can assume the _subset lists will be 0-2 items long. We can *also* assume that each player is pulled into, at most, one masonry a night. This implies that every masonry in a _subset list will have a different round number.
	#this lets us shortcut comparisons by just checking the round number.
	#we also know new masonries will be added at the bottom.
	masonries_removed = False
	while masonries_then_idx < len(masonries_then_subset) and masonries_now_idx < len(masonries_now_subset):
		round_number_comparison = masonries_then_subset[masonries_then_idx][2] - masonries_now_subset[masonries_now_idx][2]
		if round_number_comparison == 0:
			#these masonries are equal. Nothing has changed here.
			masonries_then_idx += 1
			masonries_now_idx += 1
		else: #implies round_number_comparison < 0
			#the 'then' masonry is older - it's closed.
			masonries_removed = True
			if not has_printed_anything:
				print()
				has_printed_anything = True
			print_masonry_removed(masonries_then_subset[masonries_then_idx], player_idx, masonries_now_subset, masonries_then_subset, liveness_now, liveness_then)
			masonries_then_idx += 1
	if masonries_then_idx < len(masonries_then_subset):
		masonries_removed = True
		if not has_printed_anything:
			print()
			has_printed_anything = True
		for masonry in masonries_then_subset[masonries_then_idx:]:
			print_masonry_removed(masonry, player_idx, masonries_now_subset, masonries_then_subset, liveness_now, liveness_then)
	if masonries_now_idx < len(masonries_now_subset):
		if masonries_removed or not has_printed_anything:
			print() #add line break
			has_printed_anything = True
		for masonry in masonries_now_subset[masonries_now_idx:]:
			print_masonry_added(masonry, player_idx)
		
	
def print_masonry_removed(masonry, player_idx, masonries_now_subset, masonries_then_subset, liveness_now, liveness_then):
	global args, masonries_then, masonries_now
	is_first_player = player_idx == masonry[0]
	other_player = masonry[1] if is_first_player else masonry[0]
	other_player_name = qm_shared.get_player_name(other_player)
	my_entanglers =  masonry[3] if is_first_player else masonry[4]
	their_entanglers =  masonry[4] if is_first_player else masonry[3]
	#now figure out why
	#we have the following possibilities:
	if liveness_now[other_player][1] != '#':
		#1. The other player 100% died. Easy check via liveness.
		reason = "they died"
	elif all(liveness_now[entangler_idx][1] != '#' or liveness_now[entangler_idx][0] != '#' for entangler_idx in my_entanglers):
		#2. You ran out of entanglers. Easy-ish check via liveness BUT it will miss cases where one or more entanglers became not-entanglers but didn't coalesce into a single flip.
		reason = "you were never pulled into it to begin with"
	elif all(liveness_now[entangler_idx][1] != '#' or liveness_now[entangler_idx][0] != '#' for entangler_idx in their_entanglers):
		#3. The other player ran out of entanglers. See #2.
		reason = f"{other_player_name} was never pulled into it to begin with"
	elif len(masonries_now_subset) == 2 and len(masonries_then_subset) == 2 and masonries_then_subset[1][2] == masonries_now_subset[0][2] and args.daynight == 'day' and masonries_now_subset[1][2] == args.num - 1:
		#4. You were bumped by creation of a new masonry. Easy check... you need two masonries BEFORE and two masonries NOW. The one that disappeared has to be the oldest.
		other_player_name_new = qm_shared.get_player_name(masonries_now_subset[1][1 if player_idx == masonries_now_subset[1][0] else 0])
		reason = f"it was replaced by your new masonry with {other_player_name_new} (see below)"
	else:
		other_player_now_subset = [masonry for masonry in masonries_now if masonry[0] == other_player or masonry[1] == other_player]
		other_player_then_subset = [masonry for masonry in masonries_then if masonry[0] == other_player or masonry[1] == other_player]
		if len(other_player_now_subset) == 2 and len(other_player_then_subset) == 2 and other_player_then_subset[1][2] == other_player_now_subset[0][2] and args.daynight == 'day' and other_player_now_subset[1][2] == args.num - 1:
			reason = f"{other_player_name} gained a new masonry, replacing this one"
			#5. The OTHER player bumped by creation of a new masonry. We create subsets for that other player and do the same check
		else:
			reason = "**UNKNOWN REASON, MOD NEEDS TO FIGURE THIS OUT**"
			#6. If we got here, ask for mod help.
	### THIS WILL BE WRONG OCCASIONALLY!
	print(f"**Your masonry with {other_player_name} has collapsed** - {reason}.")
	

def print_masonry_added(masonry, player_idx):
	is_first_player = player_idx == masonry[0]
	other_player = qm_shared.get_player_name(masonry[1] if is_first_player else masonry[0])
	possible_entanglers_nums = masonry[3][:] if is_first_player else masonry[4][:]
	skip_main_print = False
	if player_idx in possible_entanglers_nums:
		if len(possible_entanglers_nums) == 1:
			print(f'**You have pulled yourself into a masonry with {other_player}!**')
			skip_main_print = True
		else:
			possible_entanglers_nums.remove(player_idx)
			possible_entanglers = [qm_shared.get_player_name(item) for item in possible_entanglers_nums]
			possible_entanglers.insert(0,"yourself")
	else:
		possible_entanglers = [qm_shared.get_player_name(item) for item in possible_entanglers_nums]
	if not skip_main_print:	
		print(f'**You have been pulled into a masonry with {other_player},** by {"one of " if len(possible_entanglers) > 1 else ""}{qm_shared.oxford_comma(possible_entanglers, "or")}.')
		

def print_codeword(player_idx):
	print()
	print(f"Remember, your codeword is {qm_shared.get_player_codeword(player_idx)}.")

def print_dms():
	global args, masonries_now
	parser = argparse.ArgumentParser(
		prog='Quantumafia DM Printer',
		description='This prints DMs for day or night start in a match of Quantumafia.')
					
	parser.add_argument('daynight', help="Either 'day' or 'night', without quotes. Indicates whether to print start-of-day or start-of-night PMs.")
	parser.add_argument('num', type=int, help="The day (or night) to print DMs for.")
	args = parser.parse_args()
	
	is_day = None
	if args.daynight == 'day':
		is_day = True
	if args.daynight == 'night':
		is_day = False
	if is_day is None:
		print("Please enter either 'day' or 'night'.")
		exit()
	
	
	if not is_day and args.num == 0:
		universe_now_filedesc = os.open(f"universes-D1.txt", os.O_RDONLY) #if N0, read D1 anyway
		universe_now_file = mmap.mmap(universe_now_filedesc, 0, access=mmap.ACCESS_READ)
	else:
		universe_now_filedesc = os.open(f"universes-{'D' if is_day else 'N'}{args.num}.txt", os.O_RDONLY)	#NOT the same as regular open()
		universe_now_file = mmap.mmap(universe_now_filedesc, 0, access=mmap.ACCESS_READ)
	
	
	if not ((is_day and args.num == 1) or (not is_day and args.num == 0)):
		#no 'then' file if N0/D1
		universe_then_filedesc = os.open(f"universes-{'N' if is_day else 'D'}{args.num - (1 if is_day else 0)}.txt", os.O_RDONLY)	#NOT the same as regular open()
		universe_then_file = mmap.mmap(universe_then_filedesc, 0, access=mmap.ACCESS_READ)
	else:
		universe_then_file = None
	
	#further arg parsing will be required - but first, load game info
	#also check if output files	
	
	game_setup, _, player_board_order = qm_shared.read_game_info(args.num, False)
	#game_setup is # players, # mafia, power role T/Fs
	num_players = game_setup[0] #aliases
	num_scum = game_setup[1]
	has_detective = game_setup[2]
	has_entangler = game_setup[3]
	has_follower = game_setup[4]
	has_guard = game_setup[5]
	
	universe_now_file.seek(0)
	current_setup_string = universe_now_file.readline().decode('utf-8').rstrip('\n')
	setup_string_list = current_setup_string.split(sep="-", maxsplit=2)
	current_setup = [int(setup_string_list[0]), int(setup_string_list[1]), *[char == '1' for char in setup_string_list[2]]] #num players, num mafia, detective, entangler, follower, guard
	player_liveness_string = universe_now_file.readline().decode('utf-8').rstrip('\n')
	player_liveness = [player_liveness_string[x*2:(x+1)*2] for x in range(num_players)]
	num_universes = int(universe_now_file.readline().decode('utf-8').rstrip('\n'))
	actions = universe_now_file.readline().decode('utf-8').rstrip('\n') #assume these are correct - were validated in night. Not used elsewhere.
	
	if is_day and args.num == 1 and has_entangler:
		with open("actions-D1.txt", 'r') as actionfile:
			actions = actionfile.readline().rstrip("\n") #read supplementary actions
	
	num_players_left = current_setup[0] #aliases
	num_scum_left = current_setup[1]
	has_detective_right_now = current_setup[2]
	has_entangler_right_now = current_setup[3]
	has_follower_right_now = current_setup[4]
	has_guard_right_now = current_setup[5]
	
	
	if (is_day and args.num == 1) or (not is_day and args.num == 0):
		player_liveness_then = player_liveness #copy is fine
		num_universes_disappeared = 0 #no collapse yet
		has_detective_right_then = has_detective_right_now
		has_entangler_right_then = has_entangler_right_now
		has_follower_right_then = has_follower_right_now
		has_guard_right_then = has_guard_right_now
	else:
		universe_then_file.seek(0)
		#we need current setup before transition to be able to parse actions.
		current_setup_string_then = universe_then_file.readline().decode('utf-8').rstrip('\n')
		setup_string_list_then = current_setup_string_then.split(sep="-", maxsplit=2)
		current_setup_then = [int(setup_string_list_then[0]), int(setup_string_list_then[1]), *[char == '1' for char in setup_string_list_then[2]]]
		has_detective_right_then = current_setup_then[2]
		has_entangler_right_then = current_setup_then[3]
		has_follower_right_then = current_setup_then[4]
		has_guard_right_then = current_setup_then[5]
		player_liveness_then_string = universe_then_file.readline().decode('utf-8').rstrip('\n')
		player_liveness_then = [player_liveness_then_string[x*2:(x+1)*2] for x in range(num_players)]
		num_universes_then = int(universe_then_file.readline().decode('utf-8').rstrip('\n'))
		universe_then_file.readline() #skip actions string

		num_universes_disappeared = num_universes_then - num_universes
		
		if not is_day:
			universe_then_file.close() #clean up
			os.close(universe_then_filedesc)
	
	#remember that liveness is two characters: first is role if 100%, second is liveness (# alive, X 100% dead, V voted out)
	
	player_names = qm_shared.read_player_names()
	
	
	if is_day:
		entangler_only = False
		if args.num == 1:
			if not has_entangler:
				print("This game has no entangler, so there are no DMs for day 1. Send out night DMs as first DMs instead.")
				exit()
			entangler_only = True
		#parse player actions (same way as night.py. this could totally be more efficient but what-ever)
		player_action_blocs = [st for st in actions.split(sep="-", maxsplit=num_players-1)]
		
		if not entangler_only:
			scum_index = 0
			detective_index = scum_index + (1 if has_detective_right_then else 0)
			entangler_index = detective_index + (1 if has_entangler_right_then else 0) 
			follower_index = entangler_index + (1 if has_follower_right_then else 0) 
			guard_index = follower_index + (1 if has_guard_right_then else 0) 
		else:
			entangler_index = 0
			
		if not entangler_only:
			nightkill_requests =  [qm_shared.player_to_pos(target) if target != '#' else None for target in (player_action[scum_index] if player_liveness_then[idx][1] == '#' else '#' for idx, player_action in enumerate(player_action_blocs))]
		
			if has_detective_right_then:
				detective_requests = [qm_shared.player_to_pos(target) if target != '#' else None for target in (player_action[detective_index] if player_liveness_then[idx][1] == '#' else '#' for idx, player_action in enumerate(player_action_blocs))]
			
			if has_follower_right_then:
				follower_requests = [qm_shared.player_to_pos(target) if target != '#' else None for target in (player_action[follower_index] if player_liveness_then[idx][1] == '#' else '#' for idx, player_action in enumerate(player_action_blocs))]
		
			if has_guard_right_then:
				guard_requests = [qm_shared.player_to_pos(target) if target != '#' else None for target in (player_action[guard_index] if player_liveness_then[idx][1] == '#' else '#' for idx, player_action in enumerate(player_action_blocs))]
	
		if has_entangler_right_then:
			entangler_requests = [qm_shared.player_to_pos(target) if target != '#' else None for target in (player_action[entangler_index] if player_liveness_then[idx][1] == '#' else '#' for idx, player_action in enumerate(player_action_blocs))]
	
	
		#set up tracking lists
		results = [[[0,0,0], [0,0,0,0,0], [0,0,0]] if item[1] == '#' else None for item in player_liveness] #scum results [success, already dead, fought off by guard], det results [town align, town power, entangler, scum, dead], guard results [no activity, fought off scum, target was already dead]
		#entangler results are tracked separately by masonry, so we compute them later
		#follower result matrix separate (tracking who visited who)
		#follower stuff explained: the follower tracks when anyone VISITS another player. That's alpha scum doing a NK, guard taking up their position, and detective investigating.
		#so we track for each living player, T/F for each of those modes. Then we can parse out who visited who and yield the results to anyone who asks and could have been follower during THEN.
		follower_visits = [[False, False, False] if item[1] == '#' else None for item in player_liveness_then] #this tracks players actively visiting, not being visited. We boil that down later.
		who_visited_them = [[] if item[1] == '#' else None for item in player_liveness_then] #this tracks being visited.
		can_have_been_entangler = [False for item in player_liveness]
		can_have_been_follower = [False for item in player_liveness]
		counts = [[[0,0,0,0,0],0,[0,0],0,0,0,0,0] if item[1] == '#' else None for item in player_liveness] #dead now as [det, ent, follower, guard, town], dead before, [alpha scum, backup scum], det, ent, follower, guard, town (can't die from nightkill as scum)
		live_indexes_then = [idx for idx, item in enumerate(player_liveness_then) if item[1] == '#']
		live_indexes = [idx for idx, item in enumerate(player_liveness) if item[1] == '#']
		
		for _ in range(num_universes):
			universe_now_block = qm_shared.parse_universe(universe_now_file.readline())
			universe_now = universe_now_block[1]
			if universe_then_file is not None:
				universe_then = read_to_universe_with_id(universe_then_file, int(universe_now_block[0]))[1]
			else:
				universe_then = universe_now #D1: no previous universe to go back to

			for player_idx in live_indexes_then:
				#so unlike the night version, we need to track BOTH the role count AND the result.
				role = universe_now[player_idx]
				if role in 'XV':
					#dead. so did they JUST die?
					#we don't bother to track results in this case, because if they died just now, obviously they were scum, they failed as the guard, and get no results as the detective.
					role_then = universe_then[player_idx]
					#this bit has guardrails. We need to track if the player was the guard last night, because then their visit is added to the follower list. Else do nothing. Can throw an error if trying to update their result counts.
					player_cidx = None
					if role_then in 'XV':
						#they were dead before.	
						if counts[player_idx] is not None:
							counts[player_idx][1] += 1
						continue
					elif role_then == 'D':
						player_cidx = 0
					elif role_then == 'E':
						player_cidx = 1
					elif role_then == 'F':
						player_cidx = 2
						if counts[player_idx] is not None:
							can_have_been_follower[player_idx] = True
					elif role_then == 'G':
						#mark guard visit even if the guard is dead now
						guard_target = guard_requests[player_idx]
						gtarget_role_then = universe_then[guard_target]
						if gtarget_role_then != 'X':
							#guard visits if the player was alive before
							follower_visits[player_idx][2] = True
						player_cidx = 3
					elif role_then == 'T':
						player_cidx = 4
					if counts[player_idx] is not None:
						counts[player_idx][0][player_cidx] += 1
					continue
				if role == 'A':
					#alpha scum.
					counts[player_idx][2][0] += 1
					#track nightkill result also
					if not entangler_only:
						nk_target = nightkill_requests[player_idx]
						target_role_now = universe_now[nk_target]
						target_role_then = universe_then[nk_target]
						if target_role_now == 'X':
							#successful nightkill - or the target was dead already
							if target_role_then == 'X':
								#target was dead already
								results[player_idx][0][1] += 1
							else:
								#successful nightkill
								follower_visits[player_idx][0] = True
								results[player_idx][0][0] += 1
						else:
							#failed nightkill - assume fought off by guard
							follower_visits[player_idx][0] = True
							results[player_idx][0][2] += 1
					continue
				if role in 'BC':
					counts[player_idx][2][1] += 1
					#no results to update, no follower visits
					continue
				if role == 'D':
					counts[player_idx][3] += 1
					if not entangler_only:
						#track detective result also, and follower visits
						det_target = detective_requests[player_idx]
						itarget_role_now = universe_now[det_target]
						itarget_role_then = universe_then[det_target]
						if itarget_role_then != 'X':
							#detective visits if the player was alive before
							follower_visits[player_idx][1] = True
						if itarget_role_now == 'X': #dead
							results[player_idx][1][4] += 1
						elif itarget_role_now in 'ABC': #scum
							results[player_idx][1][3] += 1
						#we don't check for detective. WE'RE the detective!
						elif itarget_role_now == 'E': #entangler
							results[player_idx][1][2] += 1
						elif itarget_role_now in 'FG': #follower or guard (town power)
							#results[player_idx][1][0] += 1
							results[player_idx][1][1] += 1
						elif itarget_role_now == 'T':
							results[player_idx][1][0] += 1
					continue
				if role == 'E':
					can_have_been_entangler[player_idx] = True
					counts[player_idx][4] += 1
					#no visits to track, results not computed here
					continue
				if role == 'F':
					can_have_been_follower[player_idx] = True
					#no visits to track, results computed everywhere else
					counts[player_idx][5] += 1
					continue
				if role == 'G':
					counts[player_idx][6] += 1
					if not entangler_only:
						guard_target = guard_requests[player_idx]
						gtarget_role_then = universe_then[guard_target]
						if gtarget_role_then != 'X':
							#guard visits if the player was alive before
							follower_visits[player_idx][2] = True
							#now we need to get last night's nightkill target so we can check if we fought someone off
							alpha_scum_idx = universe_now.index('A')
							nk_target = nightkill_requests[alpha_scum_idx]
							if nk_target == guard_target:
								#successfully fought off
								results[player_idx][2][1] += 1
							else:
								#guard whiffed - uneventful night
								results[player_idx][2][0] += 1
						else:
							results[player_idx][2][2] += 1 #never mind, they were dead before
					continue
				if role == 'T':
					counts[player_idx][7] += 1
					#no visits or results
					continue

		universe_now_file.close()
		os.close(universe_now_filedesc)
		if not entangler_only:
			universe_then_file.close()
			os.close(universe_then_filedesc)

		#now track follower visits			
		if not entangler_only:
			for player_idx, item in enumerate(follower_visits): #by person
				if item is not None:
					for subidx, subitem in enumerate(item): #by action
						if subitem: #there was a visit by this role
							if subidx == 0: #get nightkill target
								target = nightkill_requests[player_idx]
							elif subidx == 1: #get detective target
								target = detective_requests[player_idx]
							elif subidx == 2: #get guard target
								target = guard_requests[player_idx]
							if player_idx not in who_visited_them[target]:
								who_visited_them[target].append(player_idx)
					
			follower_results = [who_visited_them[follower_requests[idx]] if was_follower else None for idx, was_follower in enumerate(can_have_been_follower)]
		
		read_masonry_differences()
		pulled_into_masonry_last_night = [False for _ in player_liveness_then]
		for masonry in (masonry for masonry in masonries_now if masonry[2] == args.num - 1): #only consider masonries made today
			pulled_into_masonry_last_night[masonry[0]] = True
			pulled_into_masonry_last_night[masonry[1]] = True
		
		#now we need to determine if there was general success at masonry-making
		entangler_results = [pulled_into_masonry_last_night[entangler_requests[idx]] if was_entangler else None for idx, was_entangler in enumerate(can_have_been_entangler)]
		
		#OK, we're finally ready to print DMs.
		
		for player_idx in live_indexes:
			print(f"DM for {qm_shared.get_player_name(player_idx)}:")
			print()
			print(f"**DAY {args.num}**")	
			player_counts = counts[player_idx]	
			player_results = results[player_idx]
			
			if entangler_only: #day 1	
				#note that we don't handle the case where a player is 0% dead and 100% some role...
				print(f'{num_universes:,} universes remain.\n')
				if sum(player_counts[2]) > 0: #scum
					total_scum = sum(player_counts[2])
					alpha_scum = player_counts[2][0]
					print(f'As **scum**, you are alive in {percent(total_scum, num_universes)} universe{plural(total_scum)}, and **alpha scum** in {percent(alpha_scum, num_universes) if alpha_scum > 0 else "none"}.')
						
				if player_counts[3] > 0: #detective
					print(f"As the **detective**, you are alive in {percent(player_counts[3], num_universes)} universe{plural(player_counts[3])}.")
					
				if player_counts[4] > 0: #entangler
					#track night action
					if entangler_requests[player_idx] is not None:
						ent_target = "yourself" if player_idx == entangler_requests[player_idx] else qm_shared.get_player_name(entangler_requests[player_idx])
						if entangler_results[player_idx]:
							ent_result = f"**you successfully pulled {ent_target} into a masonry!**"
						else:
							ent_result = f"**you tried to pull {ent_target} into a masonry**, but failed."	
					else:
						ent_result = "**nothing happened.**"
					
					print(f"As the **entangler**, you are alive in {percent(player_counts[4], num_universes)} universe{plural(player_counts[4])}.\n{tab()}Last night, {ent_result}")
					
				if player_counts[5] > 0: #follower
					print(f"As the **follower**, you are alive in {percent(player_counts[5], num_universes)} universe{plural(player_counts[5])}.")		
				if player_counts[6] > 0: #guard
					print(f"As the **guard**, you are alive in {percent(player_counts[6], num_universes)} universe{plural(player_counts[6])}.")		
				if player_counts[7] > 0: #town
					print(f"As **vanilla town**, you are alive in {percent(player_counts[7], num_universes)} universe{plural(player_counts[7])}.")		
			
			elif num_universes == 1:
				if num_universes_disappeared > 0:
					print(f"**Last night, {num_universes_disappeared:,} universes collapsed. One universe remains:**")
				else:
					print("A single universe remains.")
				#don't track dead in this case, they're alive in THIS universe and that's what matters
				if sum(player_counts[2]) > 0:
					#if not alpha scum, get their results instead - cheap way is to just find the scum player (there will only be one) and read out THEIR results.
					scum_result = ((idx, player_results[0]) for idx, player_results in enumerate(results) if sum(player_results[0]) > 0).next()
					nk_target = qm_shared.get_player_name(nightkill_requests[scum_result[0]])
					if scum_result[1][0] > 0:
						#success
						result = f"You **sucessfully killed {nk_target}** last night."
					elif scum_result[1][1] > 0:
						#already dead
						result = f"**{nk_target} was already dead** last night."
					elif scum_result[1][2] > 0:
						#fought off
						result = f"Last night, **you were fought off by the Guard** as you tried to kill **{nk_target}**."
					if num_scum_left > 1:
						other_scum_names = [qm_shared.get_player_name(idx) for idx, item in enumerate(player_liveness) if item[0] in 'ABC' and idx != player_idx]
						print(f'You are **scum**, along with {qm_shared.oxford_comma(other_scum_names,"and")}.\n{tab()}{result}')
					else:
						print(f"You are **scum** - the last one left!\n{tab()}{result}")
					
				elif player_counts[3] > 0:
					det_results = player_results[1]
					det_target = qm_shared.get_player_name(detective_requests[player_idx])
					if det_results[0] > 0 and det_results[1] == 0:
						result = "vanilla town"
					elif det_results[1] > 0:
						if not has_follower_right_now:
							result = "the guard"
						elif not has_guard_right_now:
							result = "the follower"
						else:
							result = "the follower or guard"
					elif det_results[2] > 0:
						result = "the entangler"
					elif det_results[3] > 0:
						result = "scum"
					elif det_results[4] > 0:
						result = "dead"
					print(f"You are the **detective**.\n{tab()}Upon investigating **{det_target}**, you determined they are **{result}**.")
				elif player_counts[4] > 0:
					#result is different based on if it was possible for an entangler request submit last night.
					
					if liveness_then[player_idx][0] != 'E':
						ent_target = ent_target = "yourself" if player_idx == entangler_requests[player_idx] else qm_shared.get_player_name(entangler_requests[player_idx])
						result = f"Last night, you tried to pull {ent_target} into a masonry, but **every other universe but this one collapsed**, halting the process."
					else:
						result = "Nothing happened last night."
					print(f"You are the **entangler**.\n{tab()}{result}")
				elif player_counts[5] > 0 or can_have_been_follower[player_idx] == True:
					follower_target = qm_shared.get_player_name(follower_requests[player_idx])
					if len(follower_results[player_idx]) > 0:
						#X, Y, Z,  	 A visited {} last night, in _some_ universe.
						follower_result = f'**{qm_shared.oxford_comma([qm_shared.get_player_name(player) for player in follower_results[player_idx]], "and")} {"all" if len(follower_results[player_idx]) > 1 else ""} visited {follower_target} last night**, {"each visiting " if len(follower_results[player_idx]) > 1 else ""}in _some_ surviving universe.'
					else:
						follower_result = f"**No one visited {follower_target} last night**, in any surviving universe."
					if player_counts[5] > 0:
						print(f"You are the **follower**.\n{tab()}{result}")
				elif player_counts[6] > 0:
					guard_results = player_counts[2]
					guard_target = qm_shared.get_player_name(guard_requests[player_idx])
					if guard_results[0] > 0: #no activity
						result = f"You guarded {guard_target} last night; **the night was completely uneventful**."
					elif guard_results[1] > 0: #fought off scum
						result = f"You guarded {guard_target} last night - and **fought off someone trying to kill them!**"
					elif guard_results[2] > 0: #already dead
						result = f"You tried to guard {guard_target} last night, but it turned out **they were dead before the night began**."
					print(f"You are the **guard**.\n{tab()}{result}")
				elif player_counts[7] > 0:
					print("You are **vanilla town**.")
				if player_counts[5] == 0 and can_have_been_follower[player_idx] == True:
					#TODO by the way, you WERE the follower, and...	
					print()
					print("By the way: you _were_ the **follower** in at least one universe at the start of the night. So, here are your results:")
					print(tab()+follower_result)
			else:
				if num_universes_disappeared > 0:
					print(f"**Last night, {num_universes_disappeared:,} universes collapsed. In the other {num_universes:,}:**")
				else:
					print(f"No universes collapsed last night. {num_universes:,} universes remain.")
				print()
				if(sum(player_counts[0]) > 0):
					#calculate how to say it
					dead_now = f'**You died in {percent(sum(player_counts[0]), num_universes)} universe{plural(sum(player_counts[0]))} last night.** You were {and_or_all(player_counts[0], ["the detective", "the entangler", "the follower", "the guard", "vanilla town"])}'
					if player_counts[1] > 0:
						dead_now += f", and you were already dead in {percent(player_counts[1], num_universes)} universe{plural(player_counts[1])} before the night began."
					else:
						dead_now += "."
					#you were X in all of them
					#you were X in #, and Y in #.
					#you were X in #, Y in #, and Z in #.
				else:
					dead_now = "You did not die in any universe last night."
					if player_counts[1] > 0:
						dead_now += f" You were already dead in {percent(player_counts[1], num_universes)} universe{plural(player_counts[1])} before the night began."
				#display dead
				print(dead_now)
				print()
				
				#As scum, you are alive in # universes, and alpha scum in [# / none]. 
				#In the universes where you are alpha scum, You killed # in all of them.
				#You killed # in # of them, and were fought off by the guard in [the other #.]
				if sum(player_counts[2]) > 0:
					total_scum = sum(player_counts[2])
					alpha_scum = player_counts[2][0]
					print(f'As **scum**, you are alive in {percent(total_scum, num_universes)} universe{plural(total_scum)}, and **alpha scum** in {percent(alpha_scum, num_universes) if alpha_scum > 0 else "none"}.')
					if alpha_scum > 0:
						num_results = len([x for x in player_results[0] if x > 0]) 
						nk_target = qm_shared.get_player_name(nightkill_requests[player_idx])
						
						if num_results == 1:
							scum_outcome = f"Last night, in the {alpha_scum:,} universe{plural(alpha_scum)} where you are alpha scum, "
							if player_results[0][0] > 0: #success
								scum_outcome += f"**you successfully killed {nk_target}**."
							elif player_results[0][1] > 0: #already dead
								scum_outcome += f"you tried to kill {nk_target}, but **they were already dead when you got there**."
							elif player_results[0][2] > 0: #blocked by guard
								scum_outcome += f"you tried to kill {nk_target}, but **were fought off by the guard**."
						else:
							scum_outcome = f"Last night, in the {alpha_scum:,} universe{plural(alpha_scum)} where you are alpha scum, "
							if player_results[0][0] > 0:
								scum_outcome += f"**you successfully killed {nk_target}** in {percent(player_results[0][0], alpha_scum, square_brackets=True)} of them"
								if player_results[0][2] > 0:
									scum_outcome += f", and **were fought off by the guard** in {percent(player_results[0][2], alpha_scum, square_brackets=True)}."
								else:
									scum_outcome += "."
							else: #must be guard and dead
								scum_outcome += f"you tried to kill {nk_target} in {percent(player_results[0][2], alpha_scum, square_brackets=True)} of them, but **were fought off by the guard**."
							if player_results[0][1] > 0:
								scum_outcome += f' {nk_target} **was already dead** when you got there in {percent(player_results[0][1], alpha_scum, square_brackets=True)}{" more" if num_results < 3 else ""} universe{plural(player_results[0][1])}.'
						print(tab()+scum_outcome)
						print()
						
						#you successfully killed {}. #//say # of universes
						#you tried to kill {}, but were fought off by the guard. #//say # of universes
						#you tried to kill {}, but they were already dead beforehand. #//say # of universes
						#you successfully killed {} in {} of them. {} was already dead beforehand in {} more universes.
						#you successfully killed {} in {} of them, and were fought off by the guard in {}. [{} was already dead beforehand in {} universes.]
						#you tried to kill {} in {} of them, but were fought off by the guard. {} was already dead beforehand in {} more universes.	
				else:
					print("You are not alive as scum in any universe.")
					print()
					
				if player_counts[3] > 0: #detective
					det_target = qm_shared.get_player_name(detective_requests[player_idx])
					#As the Detective, you investigated # (and are alive) in # universes (#%). They are town-aligned in # of them, and hold a town-aligned power role in [# / none] of those. They are the Entangler in # universes where you are alive, and scum 
					detective_result = f"As the **detective**, you investigated {det_target} (and are alive) in {percent(player_counts[3], num_universes)} universe{plural(player_counts[3])}."
					num_results = len([x for x in player_results[1] if x > 0]) 
					
					if num_results == 1: #or (num_results == 2 and player_results[1][0] > 0 and player_results[1][1] == player_results[1][0]):
						#only one outcome, simple messages (also handles case where there is only one universe left)
						multiple_universes =  not (sum(player_results[1]) - player_results[1][1] == 1)
						if player_results[1][4] > 0: #dead
							detective_result += f'\n{tab()}However, they are dead in {"each of those" if multiple_universes else "that"} universe{"s" if multiple_universes else ""}.'
						else:
							if player_results[1][1] > 0: #town power
								if not has_follower_right_now:
									role = "a town power role (i.e. the **guard**)"
								elif not has_guard_right_now:
									role = "a town power role (i.e. the **follower**)"
								else:
									role = "a town power role (the **follower or guard**)"
							elif player_results[1][0] > 0: #town (vanilla)
								role = "**vanilla town**"
							elif player_results[1][2] > 0: #entangler
								role = "the **entangler**"
							elif player_results[1][3] > 0: #scum
								role = "**scum**"
							detective_result += f'\n{tab()}They are {role} in {"each" if multiple_universes else "that"} universe.'
					else:
						if not has_follower_right_now:
							role = "i.e. the guard"
						elif not has_guard_right_now:
							role = "i.e. the follower"
						else:
							role = "the follower or guard"
						detective_result += "\n{}They {}.".format(tab(), and_or_all(player_results[1], ["are **vanilla town**", "hold a **town power role** ({})".format(role), "are the **entangler**", "are **scum**", "are **dead**"], include_percents=True))
						if player_results[1][4] == 0:
							detective_result += " They are **not dead** in any universe you investigated."
	
					print(detective_result)
					print()
				elif has_detective_right_now:
					print("You are not alive as the detective in any universe.")
					print()

				if player_counts[4] > 0: #entangler
					if entangler_requests[player_idx] is not None:
						ent_target = "yourself" if player_idx == entangler_requests[player_idx] else qm_shared.get_player_name(entangler_requests[player_idx])
					if player_counts[4] == num_universes:
						#only one entangler - can't submit.
						if liveness_then[player_idx][0] != 'E':
							print(f"As the **entangler**, you are alive in {player_counts[4]:,} universes - that's every universe.\n{tab()}Last night, you tried to pull **{ent_target}** into a masonry, but **every universe with a different entangler collapsed**. Sorry!")
						else: 
							print(f"As the **entangler**, you are alive in {player_counts[4]:,} universes - that's every universe.\n{tab()}Nothing happened last night.")
					else:
						if entangler_results[player_idx]:
							ent_result = f"**successfully pulled {ent_target} into a masonry!**"
						else:
							ent_result = f"**tried to pull {ent_target} into a masonry**, but failed."
						print(f"As the **entangler**, you are alive in {percent(player_counts[4], num_universes)} universe{plural(player_counts[4])}.\n{tab()}Last night, you {ent_result}")
						print()
				elif has_entangler_right_now:
					print("You are not alive as the entangler in any universe.")
					print()

				if follower_results[player_idx] is not None:
					follower_target = qm_shared.get_player_name(follower_requests[player_idx])
					if len(follower_results[player_idx]) > 0:
						#X, Y, Z, and/or A visited {} last night, in _some_ universe.
						follower_result = f'**{qm_shared.oxford_comma([qm_shared.get_player_name(player) for player in follower_results[player_idx]], "and")} {"all " if len(follower_results[player_idx]) > 1 else ""}visited {follower_target} last night**, {"each visiting " if len(follower_results[player_idx]) > 1 else ""}in _some_ surviving universe.'
					else:
						follower_result = f"**No one visited {follower_target} last night**, in any surviving universe."
					
				if player_counts[5] > 0: #follower
					print(f"As the **follower**, you are alive in {percent(player_counts[5], num_universes)} universe{plural(player_counts[5])}.\n{tab()}{follower_result}")		
					print()
				elif has_follower_right_now:
					if can_have_been_follower[player_idx]:
						print(f"You are not alive as the **follower** in any universe... but you _were_ last night, so you get those results anyway.\n{tab()}{follower_result}")
						print()
					else:
						print("You are not alive as the follower in any universe.")
						print()
					
				if player_counts[6] > 0: #guard
					guard_target = qm_shared.get_player_name(guard_requests[player_idx])
					guard_result = f'As the **guard**, you protected {guard_target} (and are alive) in {percent(player_counts[6], num_universes)} universe{plural(player_counts[6])}.\n{tab()}'
					num_results = len([x for x in player_results[2] if x > 0]) 
					multiple_universes = sum(player_results[2]) > 1
					
					if num_results == 1:
						if player_results[2][0] > 0: #no activity
							guard_result += f'**Your night was uneventful{" in all of them" if multiple_universes else ""}**.'
						elif player_results[2][1] > 0: #fought off
							guard_result += f'**You fought off someone trying to kill {guard_target}{" in all of them" if multiple_universes else ""}**!'
						elif player_results[2][2] > 0: #already dead
							guard_result += f'Sadly, {guard_target} **was already dead when you got there**{", in all the universes you made the attempt" if multiple_universes else ""} - they had died before the night began.'
					else:
						
						#"You had an uneventful night in {}
						if player_results[2][2] > 0 and num_results < 3:
							guard_result += 'You '
							if player_results[2][0] > 0:
								guard_result += f'**had an uneventful night** in {percent(player_results[2][0], player_counts[6], square_brackets=True)} of them.'
							else: #implies must have fought off
								f"**fought off someone trying to kill {guard_target}** in {percent(player_results[2][1], player_counts[6], square_brackets=True)} of them."
						else:
							guard_result += 'You '+and_or_all(player_results[2], ["**had an uneventful night**", f"**fought off someone trying to kill {guard_target}**"], include_percents=True, override_total=player_counts[6])+'.'
						if player_results[2][2] > 0:
							guard_result += f' {guard_target} **was already dead when you got there** in {percent(player_results[2][2], player_counts[6], square_brackets=True)} universe{plural(player_results[2][2])}.'
					print(guard_result)
					print()
				elif has_guard_right_now:
					print("You are not alive as the guard in any universe.")
					print()

				if player_counts[7] > 0: #town
					print(f"As **vanilla town**, you are alive in {percent(player_counts[7], num_universes)} universe{plural(player_counts[7])}.")		
				else:
					print("You are not alive as vanilla town in any universe.")

			if has_entangler_right_now:
				print_masonry_differences(player_idx, player_liveness, player_liveness_then)
		
			#and codeword
			print_codeword(player_idx)
			print()		
	else:
		#if it's night mode, we don't need to track anything between universes except how many universes there were then vs now
		
		counts = [[0,[0,0],0,0,0,0,0] if item[1] == '#' else None for item in player_liveness] #dead, [alpha scum, backup scum], det, ent, follower, guard, town
		live_indexes = [idx for idx, item in enumerate(player_liveness) if item[1] == '#']
		
		for _ in range(num_universes): #calculate counts
			universe = qm_shared.parse_universe(universe_now_file.readline())[1]
			for player_idx in live_indexes:
				role = universe[player_idx]
				if role in 'XV':
					counts[player_idx][0] += 1
					continue
				if role == 'A':
					counts[player_idx][1][0] += 1
					continue
				if role in 'BC':
					counts[player_idx][1][1] += 1
					continue
				if role == 'D':
					counts[player_idx][2] += 1
					continue
				if role == 'E':
					counts[player_idx][3] += 1
					continue
				if role == 'F':
					counts[player_idx][4] += 1
					continue
				if role == 'G':
					counts[player_idx][5] += 1
					continue
				if role == 'T':
					counts[player_idx][6] += 1
					continue
	
		universe_now_file.close()
		os.close(universe_now_filedesc)
	
		for player_idx in live_indexes:
			print(f"DM for {qm_shared.get_player_name(player_idx)}:")
			print()
			print(f"**NIGHT {args.num}**")
			night_actions = []
			if num_universes == 1:
				if num_universes_disappeared > 0:
					print(f"Today, {num_universes_disappeared} universes collapsed. One universe remains:")
				else:
					print("A single universe remains.")
				print()
				if sum(counts[player_idx][1]) > 0:
					if num_scum_left > 1:
						other_scum_names = [qm_shared.get_player_name(idx) for idx, item in enumerate(player_liveness) if item[0] in 'ABC' and idx != player_idx]
						print(f'You are **scum**, along with {qm_shared.oxford_comma(other_scum_names,"and")}.')
						night_actions.append("**Please** (collaboratively) **choose someone to nightkill,** and submit your target in scumchat.")
					else:
						print("You are **scum** - the last one left!")
						night_actions.append("**Please choose someone to nightkill.**")
					
				elif counts[player_idx][2] > 0:
					print("You are the **detective**.")
					night_actions.append("**Please choose someone to investigate.**")
				elif counts[player_idx][3] > 0:
					print("You are the **entangler** - though with just one universe, it's about equivalent to being vanilla town at this point. Sorry!")
				elif counts[player_idx][4] > 0:
					print("You are the **follower**.")
					night_actions.append("**Please choose someone to watch.**")
				elif counts[player_idx][5] > 0:
					print("You are the **guard**.")
					night_actions.append("**Please choose someone to protect.**")
				elif counts[player_idx][5] > 0:
					print("You are **vanilla town**.")
			else:
				if num_universes_disappeared > 0:
						print(f"Today, {num_universes_disappeared:,} universes collapsed. In the other {num_universes:,}:")
				else:
					print(f'{"No universes collapsed today. " if args.num > 0 else ""}{num_universes} universes remain.\n')
				print()
				player_counts = counts[player_idx]	
				
				if player_counts[0] > 0:
					dead_in = player_counts[0]
					print(f"You are dead in {percent(dead_in, num_universes)} universe{plural(dead_in)}.")
				else:
					print("You are not dead in any universe.")
					
				#note that we don't handle the case where a player is 0% dead and 100% some role...
				if sum(player_counts[1]) > 0: #scum
					total_scum = sum(player_counts[1])
					alpha_scum = player_counts[1][0]
					print(f'As **scum**, you are alive in {percent(total_scum, num_universes)} universe{plural(total_scum)}, and **alpha scum** in {percent(alpha_scum, num_universes) if alpha_scum > 0 else "none"}.')
					if alpha_scum > 0 and args.num > 0:
						night_actions.append("**Please choose someone to nightkill.**")
				else:
					print("You are not alive as scum in any universe.")
						
				if player_counts[2] > 0: #detective
					print(f"As the **detective**, you are alive in {percent(player_counts[2], num_universes)} universe{plural(player_counts[2])}.")
					if args.num > 0:
						night_actions.append("**Please choose someone to investigate.**")
				elif has_detective_right_now:
					print("You are not alive as the detective in any universe.")
					
				if player_counts[3] > 0: #entangler
					if player_counts[3] == num_universes:
						print(f"As the **entangler**, you are alive in {player_counts[3]} universes - that's every universe, so there are no entanglers in other universes to entangle with. Sorry!")
					else:
						print(f"As the **entangler**, you are alive in {percent(player_counts[3], num_universes)} universe{plural(player_counts[3])}.")
						night_actions.append("**Please choose someone to** (try to) **pull into a masonry.**")
				elif has_entangler_right_now:
					print("You are not alive as the entangler in any universe.")
					
				if player_counts[4] > 0: #follower
					print(f"As the **follower**, you are alive in {percent(player_counts[4], num_universes)} universe{plural(player_counts[4])}.")		
					if args.num > 0:
						night_actions.append("**Please choose someone to watch.**")
				elif has_follower_right_now:
					print("You are not alive as the follower in any universe.")
					
				if player_counts[5] > 0: #guard
					print(f"As the **guard**, you are alive in {percent(player_counts[5], num_universes)} universe{plural(player_counts[5])}.")		
					if args.num > 0:
						night_actions.append("**Please choose someone to protect.**")
				elif has_guard_right_now:
					print("You are not alive as the guard in any universe.")
					
				if player_counts[6] > 0: #town
					print(f"As **vanilla town**, you are alive in {percent(player_counts[6], num_universes)} universe{plural(player_counts[6])}.")		
				else:
					print("You are not alive as vanilla town in any universe.")
			
			#either way, now handle masonries
			if has_entangler_right_now and args.num > 0:
				#print()
				print_masonry_differences(player_idx, player_liveness, player_liveness_then)
			
			print()
			if len(night_actions) > 0:
				print("Tonight:")
				for action in night_actions:
					print(action)
			else:
				print("You have no night actions.")
			
			#and codeword
			print_codeword(player_idx)
			print()
	###NIGHT BLOCK ENDS HERE
	
	aggregated_counts = [[0,0,0,0,0] if item[1] == '#' else None for item in player_liveness]
	for idx, player_count in enumerate(counts):
		if aggregated_counts[idx] is None:
			continue #skip dead players
		#day format is [dead_now], dead_then, [scum], det, ent, fol, guard, town
		#night format is dead, [scum], det, ent, fol, guard, town
		aggregated_counts[idx][4] = sum(player_count[0])+player_count[1] if is_day else player_count[0] #dead
		aggregated_counts[idx][3] = sum(player_count[2 if is_day else 1]) #scum
		aggregated_counts[idx][2] = player_count[4 if is_day else 3] #entangler
		aggregated_counts[idx][1] =  player_count[5] + player_count[6 if is_day else 4] + player_count[3 if is_day else 2] #detective, follower, or guard - 3-5-6 or 2-4-5
		aggregated_counts[idx][0] = aggregated_counts[idx][1] + player_count[7 if is_day else 6]
	
	print()
	print("Public probability table:")
	has_power = has_detective or has_follower or has_guard
	print(f'Who      Town%    {"Power%   " if has_power else ""}{"Ent%     " if has_entangler else ""}Scum%    Dead%    ')
	
	aggregated_counts = [[table_percent(x / num_universes) for x in item] if item is not None else None for item in aggregated_counts]
		
	if not has_entangler:
		for item in aggregated_counts:
			if item is None:
				continue
			del item[2]
			item.append("")
	if not has_power:
		for item in aggregated_counts:
			if item is None:
				continue
			del item[1]
			item.append("")
	for player in player_board_order:
		player_idx = qm_shared.player_to_pos(player)
		if aggregated_counts[player_idx] is None:
			role_item = player_liveness[player_idx][0] 
			if role_item in 'ABC':
				role = 'SCUM'
			elif role_item == 'D':
				role = 'DETECTIVE'
			elif role_item == 'E':
				role = 'ENTANGLER'
			elif role_item == 'F':
				role = 'FOLLOWER'
			elif role_item == 'G':
				role = 'GUARD'
			elif role_item == 'T':
				role = 'TOWN'
			print(f'{qm_shared.get_player_codeword(player_idx)}      {qm_shared.get_player_name(player_idx)} - {"voted out" if player_liveness[player_idx][1] == "V" else "100% dead"} - {role}')
		else:
			print('{}    {}{}{}{}{}'.format(qm_shared.get_player_codeword(player_idx), *aggregated_counts[player_idx]))
			
			
			
	if args.num > 0:
		print()	
	print(f'{num_universes:,} universe{"s" if num_universes > 1 else ""} remain{"" if num_universes > 1 else "s"}.')	
	if args.num > 0:
		print()
		print_masonry_count_diff()
	
	#AND WE ARE DONE.
	
			
	#finally, print probability table and masonry state
	#table format = 
	
	#Who     Town%   Power%  Ent%    Scum%   Dead%   #(8 spaces per block
	#CWORD	 30.5%   22.3%   0%      12.1%   9%
	#CWORD - PlayerName - voted out - SCUM
	#CWORD - PlayerName2 - 100% dead - DETECTIVE
				
				
				
				
#DM FORMAT:
	#DAY START
	#Last night, # universes collapsed. In the others:
	#you died in how many
	#As scum, you are alive in # universes, and alpha scum in [# / none]. 
		#In the universes where you are alpha scum, You killed # in all of them.
		#You killed # in # of them, and were fought off by the guard in [the other #.]
		#Dead: You are not alive as scum in any universe.
	#As the Detective, you investigated # (and are alive) in # universes (#%). They are town-aligned in # of them, and hold a town-aligned power role in [# / none] of those. They are the Entangler in # universes where you are alive, and scum 
		#*Skip blocks that are inapplicable.
		#D1 variation: As the Detective, you are alive in # universes (#%).
		#Dead variation: You are not alive as the Detective in any universe.
	#As the Entangler, you are alive in # universes (#%). Last night, you [successfully pulled # into a masonry] / [tried to pull # into a masonry,
		#TODO figure out all possible messages. report what happened and possibly why
			#tried to pull, but other people got there first
			#tried to pull, but no partners 
	#As the Follower, you are alive in # universes (#%). You examined # last night. [No one visited them in any remaining universe. / #, #, #, #, and/or # visited them in some remaining universe.]
		#D1 variation: As the Follower, you are alive in # universes (#%).
		#Dead variation: You are not alive as the Follower in any universe.
		#Dead but with a result waiting: You are not alive as the Follower in any universe... _but_ you examined # last night when you were. => segue
	#As the Guard, you guarded # (and are alive) in # universes (#%). [Your night was completely uneventful in all of them. / You fought off scum last night in # of them, and had an uneventful night in the other #. / You fought off scum last night in all of them.]
		#D1 variation: As the Guard, you are alive in # universes (#%).
		#Dead variation: You are not alive as the Guard in any universe.
	#As vanilla town, you are alive in # universes (#%).
		#Dead variation: You are not alive as vanilla town in any universe.

	#Your masonry with # has collapsed - [# has died in all universes. / [you / you and # / #] [was/were] never pulled into it. ]

	#You have been pulled into a masonry with #, by [# / one of #, #, or #].
	
	#Remember, your codeword is #####.
	
	#NIGHT START
	#Today, # universes collapsed. In the others:
	#all of the above but just the short version (incl. Masonries)
	
	#**Tonight:**
	#**Please choose a person to nightkill.** [if not backup scum]
	#**Please choose a person to investigate.**
	#**Please choose a person to pull into a masonry.**
	#**Please choose a person to watch.**
	#**Please choose a person to guard.**
	
	#OR
	
	#**You have no night actions.**
	
	
	


if __name__ == "__main__":
	print_dms()
	