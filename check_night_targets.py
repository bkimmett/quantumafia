#!/usr/bin/env python3

import argparse, random, qm_shared
from sys import exit
from os.path import exists
from functools import cmp_to_key #for sorting

def check_targets():
	parser = argparse.ArgumentParser(
						prog='Quantumafia Night Target Checker',
						description='This processes the end-of-night transition in a match of Quantumafia.')
					
	parser.add_argument('night', type=int, help="Indicates which game night (1, 2, 3...) to check targets for.")
	parser.add_argument('player', type=qm_shared.single_letter, help="Indicates which player (A, B, C, D...) needs their actions checked.")
	parser.add_argument('actions', help="A string of actions for the target player, in the order [scum][detective][entangler][follower][guard]. Sample: EMBLJ. Skip actions for players who have flipped as power roles.")
	args = parser.parse_args()
	
	#further arg parsing will be required - but first, load game info
	#also check if output files	
	
	game_setup, _, _ = qm_shared.read_game_info(args.night, False)
	#game_setup is # players, # mafia, power role T/Fs
	num_players = game_setup[0] #aliases
	num_scum = game_setup[1]
	has_detective = game_setup[2]
	has_entangler = game_setup[3]
	has_follower = game_setup[4]
	has_guard = game_setup[5]
	
	# we also want to read player liveness and current setup state from universes file
	if args.night == 0:
		print("Targets will always be valid in N0.")
		exit()
	else:	
		current_setup, player_liveness, num_universes = qm_shared.read_current_info(args.night, False)
	
	num_players_left = current_setup[0] #aliases
	num_scum_left = current_setup[1]
	has_detective_right_now = current_setup[2]
	has_entangler_right_now = current_setup[3]
	has_follower_right_now = current_setup[4]
	has_guard_right_now = current_setup[5]
	#remember that liveness is two characters: first is role if 100%, second is liveness (# alive, X 100% dead, V voted out)
	
	player_names = qm_shared.read_player_names()
	
	active_player_idx = qm_shared.player_to_pos(args.player)
	
	if active_player_idx > num_players:
		print(f"Invalid player letter. Must be A-{qm_shared.pos_to_player(num_players-1)}.")
		exit()
	
	if player_liveness[active_player_idx][1] != '#':
		print("This player is dead.")
		exit()
	
	#everything appears at least _nominally_ in order - now let's do the actual night stuff.

	if not all(ord(char) == 35 or (char.isalpha() and char.isascii()) for char in args.actions):
		print("Invalid character in actions string. Accepts only A-Z for targets, or # for 'no target'.")
		exit()
		
	aa_upper = args.actions.upper()
		
	invalid_targets_list = [qm_shared.pos_to_player(idx) for idx, item in enumerate(player_liveness) if item[1] != '#']
	invalid_targets = "".join(invalid_targets_list)
	invalid_targets_2 = "".join([qm_shared.pos_to_player(item) for item in range(num_players, 27)])
	
	if any(elem in aa_upper for elem in invalid_targets):
		print(f'This actions string has an invalid target somewhere in it. Players {", ".join(invalid_targets_list)} are 100% dead and cannot be targeted.')
		exit()
	
	if any(elem in aa_upper for elem in invalid_targets_2):
		print(f"This actions string has an invalid target somewhere in it. The highest valid player letter is {qm_shared.pos_to_player(num_players-1)}, but I've found one beyond that.")
		exit()
	
	expected_bloc_len = 1 + sum([1 if item else 0 for item in current_setup[2:]])
	
	if len(aa_upper) != expected_bloc_len:
		error = "The action block is the wrong length. "
		if expected_bloc_len == 1:
			error += "It must be 1 character long, corresponding to their nightkill. "
		else:
			error += f"It must be {expected_bloc_len} characters long, corresponding to their "
			verbs = ["nightkill"]
			if has_detective_right_now:
				verbs.append("investigation")
			if has_entangler_right_now:
				verbs.append("entanglement")
			if has_follower_right_now:
				verbs.append("watch")
			if has_guard_right_now:
				verbs.append("protect")
			error += f'{qm_shared.oxford_comma(verbs, "and")}. '
		error += "If a player is guaranteed not to be able to use a role, you can set that role's target letter to '#'."
		print(error)
		exit()
	
	#STEP -1: PARSE OUT EVERYONE'S REQUESTS.
	

	scum_index = 0
	detective_index = scum_index + (1 if has_detective_right_now else 0)
	entangler_index = detective_index + (1 if has_entangler_right_now else 0) 
	follower_index = entangler_index + (1 if has_follower_right_now else 0) 
	guard_index = follower_index + (1 if has_guard_right_now else 0) 
	
	nightkill_request = aa_upper[scum_index]
	
	if has_detective_right_now:
		detective_request = aa_upper[detective_index]
		
	if has_follower_right_now:
		follower_request = aa_upper[follower_index]
	
	if has_guard_right_now:
		guard_request = aa_upper[guard_index]
	
	if has_entangler_right_now:	
		entangler_request = aa_upper[entangler_index]	
				
	#Step 0B - track targets
	#scan through the universe list and make sure that (for each nightkill, detective, or guard) their target is alive in at least one universe (and, for nightkill, alive and not scum)

	universe_file = qm_shared.get_universe_file(args.night, False) #should return existing file pointer
	universe_file.seek(0)
	universe_file.readline() #skip 4 lines to get to actual universes
	universe_file.readline()
	universe_file.readline()
	universe_file.readline()

	targets_to_check = 0
	validate_block = {}
	target_block = {}
	if nightkill_request != '#':
		target_block['A'] = nightkill_request
		validate_block['A'] = True
		targets_to_check += 1
	if has_detective_right_now and detective_request != '#':
		target_block['D'] = detective_request
		validate_block['D'] = True
		targets_to_check += 1
	if has_entangler_right_now and entangler_request != '#':
		target_block['E'] = None #
		validate_block['E'] = True
		targets_to_check += 1
	if has_follower_right_now and follower_request != '#':
		target_block['F'] = None
		validate_block['F'] = True
		targets_to_check += 1
	if has_guard_right_now and guard_request != '#':
		target_block['G'] = guard_request
		validate_block['G'] = True
		targets_to_check += 1

	validates_to_check = targets_to_check
	#now go universe by universe
	for _ in range(num_universes):
		if targets_to_check <= 0:
			break
	
		next_universe = qm_shared.parse_universe(universe_file.readline())[1] #get second half of universe - the part with the letters	
		#check scum
		role_index = next_universe[active_player_idx]
		if role_index in target_block:
			if role_index in validate_block:
				del validate_block[role_index]
				validates_to_check -= 1
			if role_index not in 'ADG':
				del target_block[role_index]
				targets_to_check -= 1
				continue
			if next_universe[qm_shared.player_to_pos(target_block[role_index])] not in 'XV': #i.e. if not dead, or voted out...
				del target_block[role_index]
				targets_to_check -= 1
	
	if validates_to_check > 0:
		print("This player has an one or more actions for which they are not alive in any universe. They are:")
		if 'A' in validate_block:
			print("* Nightkill (alpha scum)")
		if 'D' in validate_block:
			print("* Investigation (detective)")
		if 'E' in validate_block:
			print("* Entanglement")
		if 'F' in validate_block:
			print("* Follow")
		if 'G' in validate_block:
			print("* Guard")
		exit()
		
	if targets_to_check > 0:
		print("This player is targeting other players who are dead in every universe where this player holds a role. They are:")
		for (key, value) in target_block.items():
			print(f"{player_names[active_player_idx]} {('nightkilling' if key == 'A' else ('investigating' if key == 'D' else ('guarding' if key == 'G' else 'ERROR!!!!!')))} {player_names[qm_shared.player_to_pos(value)]}.")
		exit()
	
	print("Targets validated! All appears OK.")
	
		
if __name__ == "__main__":
	check_targets()