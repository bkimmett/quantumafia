#!/usr/bin/env python3

import argparse, random, qm_shared
from sys import exit
from os.path import exists
from functools import cmp_to_key #for sorting

def night():
	parser = argparse.ArgumentParser(
						prog='Quantumafia Night Processor',
						description='This processes the end-of-night transition in a match of Quantumafia.')
					
	parser.add_argument('night', type=int, help="Indicates which game night (0, 1, 2, 3...) is to be transitioned. In Night 0, only entangler actions are considered")
	parser.add_argument('actions', help="A string of actions for each player, in the order [scum][detective][entangler][follower][guard], then different players separated by dashes in unrandomized roster order. Remove sections of that that aren't currently present in the game at ALL (if detective is dead remove the detective section, etc). Sample string will look like EGHNA-BBCDB-ANTQL-... or E-N-B-D-H on N0 when only entangler. If a particular player doesn't have a role that place in the string, that place will be ignored.")
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
		#read D1 file instead
		current_setup, player_liveness, num_universes = qm_shared.read_current_info(1, True)
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
	
	#everything appears at least _nominally_ in order - now let's do the actual night stuff.
	
	entangler_only = False
	
	if args.night == 0:
		if has_entangler:
			entangler_only = True
		else:
			print("Nothing to do for Night 0.")
			print("*** NEXT: RUN DAY.PY FOR DAY 1 ***")
		
	
	if (has_entangler_right_now or entangler_only) and exists(f"masonries-D{args.night+1}.txt"):
		print(f"The masonries file I'd have to write to, masonries-D{args.night+1}.txt, already exists. Delete the old file if you want me to overwrite it.")
		exit()
	
	if not entangler_only and exists(f"universes-D{args.night+1}.txt"):
		print(f"The universe file I'd have to write to, universes-D{args.night+1}.txt, already exists. Delete the old file if you want me to overwrite it.")
		exit()
	
	if entangler_only and exists("actions-D1.txt"):
		print(f"The supplementary actions file I'd have to write to, actions-D1.txt, already exists. Delete the old file if you want me to overwrite it.")
		exit()
	
	#now time to parse arguments properly.
	
	if not all(ord(char) == 35 or ord(char) == 45 or (char.isalpha() and char.isascii()) for char in args.actions):
		print("Invalid character in actions string. Accepts only A-Z for targets, # for 'no target', and - as a separator.")
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
	
	player_action_blocs = [st for st in aa_upper.split(sep="-", maxsplit=num_players-1)]
	expected_bloc_len = 1 if args.night == 0 else 1 + sum([1 if item else 0 for item in current_setup[2:]])
	
	if len(player_action_blocs) < num_players:
		print("I need an action block for each player, even dead ones. If a player is voted out of the game, their block can just be '#'.")
		exit()
	
	if not all(len(bloc) == expected_bloc_len or player_liveness[idx][1] != '#' for idx, bloc in enumerate(player_action_blocs)):
		error = "The action block for one or more living players are the wrong length. "
		if expected_bloc_len == 1:
			if args.night == 0:
				error += "Each must be 1 character long, corresponding to their entanglement. "
			else:
				error += "Each must be 1 character long, corresponding to their nightkill. "
		else:
			error += f"Each must be {expected_bloc_len} characters long, corresponding to their "
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
	
	if entangler_only:
		entangler_index = 0
	else:
		scum_index = 0
		detective_index = scum_index + (1 if has_detective_right_now else 0)
		entangler_index = detective_index + (1 if has_entangler_right_now else 0) 
		follower_index = entangler_index + (1 if has_follower_right_now else 0) 
		guard_index = follower_index + (1 if has_guard_right_now else 0) 
		nightkill_requests =  [player_action[scum_index] if player_liveness[idx][1] == '#' else '#' for idx, player_action in enumerate(player_action_blocs)]
		
		if has_detective_right_now:
			detective_requests = [player_action[detective_index] if player_liveness[idx][1] == '#' else '#' for idx, player_action in enumerate(player_action_blocs)]
			
		if has_follower_right_now:
			follower_requests = [player_action[follower_index] if player_liveness[idx][1] == '#' else '#' for idx, player_action in enumerate(player_action_blocs)]
		
		if has_guard_right_now:
			guard_requests = [player_action[guard_index] if player_liveness[idx][1] == '#' else '#' for idx, player_action in enumerate(player_action_blocs)]
	
	#note that we go out a level here
	if entangler_only or has_entangler_right_now:	
		entangler_requests = [player_action[entangler_index] if player_liveness[idx][1] == '#' else '#' for idx, player_action in enumerate(player_action_blocs)]
		
	#there has GOT to be a more efficient way to do all that
	

	
	#STEP 0: generate rough entangler list. We'll need to prune it later on, though.
	#MOVED TO BOTTOM
				
	#Step 0B - track targets
	#scan through the universe list and make sure that (for each nightkill, detective, or guard) their target is alive in at least one universe (and, for nightkill, alive and not scum)
	
	if not entangler_only:
	
		universe_file = qm_shared.get_universe_file(args.night, False) #should return existing file pointer
		universe_file.seek(0)
		universe_file.readline() #skip 4 lines to get to actual universes
		universe_file.readline()
		universe_file.readline()
		universe_file.readline()
	
		target_checking = []
		targets_to_check = 0
		for idx in range(num_players):
			next_target_block = {}
			if player_liveness[idx][1] == '#': #we're relying on the input to be correctly formatted, that is: that if a player isn't a role their submission for that role won't be recorded. If this does not hold true, it'll still work properly, just we'll have to check every universe when we may not necessarily have to.
				this_player_bloc = player_action_blocs[idx]
				if this_player_bloc[scum_index] != '#':
					next_target_block['A'] = this_player_bloc[scum_index]
					targets_to_check += 1
				if has_detective_right_now and this_player_bloc[detective_index] != '#':
					next_target_block['D'] = this_player_bloc[detective_index]
					targets_to_check += 1
				if has_guard_right_now and this_player_bloc[guard_index] != '#':
					next_target_block['G'] = this_player_bloc[guard_index]
					targets_to_check += 1
		
			target_checking.append(next_target_block)	
		
		#now go universe by universe
		for _ in range(num_universes):
			if targets_to_check <= 0:
				break
		
			next_universe = qm_shared.parse_universe(universe_file.readline())[1] #get second half of universe - the part with the letters	
			#check scum
			thisuni_scum_index = next_universe.index('A')
			if 'A' in target_checking[thisuni_scum_index]:
				#find scum target
				if next_universe[qm_shared.player_to_pos(target_checking[thisuni_scum_index]['A'])] not in 'XV': #i.e. if not dead, or voted out...
					del target_checking[thisuni_scum_index]['A']
					targets_to_check -= 1
			if has_detective_right_now and 'D' in next_universe:
				thisuni_det_index = next_universe.index('D')
				if 'D' in target_checking[thisuni_det_index]:
					#find det target
					if next_universe[qm_shared.player_to_pos(target_checking[thisuni_det_index]['D'])] not in 'XV':
						del target_checking[thisuni_det_index]['D']
						targets_to_check -= 1
			if has_guard_right_now and 'G' in next_universe:
				thisuni_guard_index = next_universe.index('G')
				if 'G' in target_checking[thisuni_guard_index]:
					#find guard target
					if next_universe[qm_shared.player_to_pos(target_checking[thisuni_guard_index]['G'])] not in 'XV':
						del target_checking[thisuni_guard_index]['G']
						targets_to_check -= 1
		
			
		if targets_to_check > 0:
			print("Uh-oh. Some players are targeting other players who are dead in every universe where the first player holds a role. They are:")
			for idx, player_targets in enumerate(target_checking):
				for (key, value) in player_targets.items():
					print(f"{player_names[idx]} {('nightkilling' if key == 'A' else ('investigating' if key == 'D' else ('guarding' if key == 'G' else 'ERROR!!!!!')))} {player_names[qm_shared.player_to_pos(value)]}.")
			exit()
		
		else:
			print("Targets validated. Ready!")
			input("Press ENTER to begin transforming universes.")
	
		
		#1. The Guard and Follower take up their positions, if they are alive.	
		#(we already determined follower, detective, and guard requests tbh)
	
		#before we continue, though, we need to track results for each player.
		#results are of the form:
		#[death_results, scum_result, detective_result, entangler_result, follower_result, guard_result, town_result]
		#death_results: an array indicating the number of times you died last night broken down by who you were:
			#[died_as_town, died_as_detective, died_as_entangler
		# note that all of these can be determined by scanning the list later EXCEPT the 'died when', as that requires the previous => next state change.
		# maybe we just leave all of it to the DM generator?
		# 
		# post night dm format = "Last night, # universes collapsed. In the remaining #:"  #measure this by new univcount vs old univcount
		# "You died in # universes. You were the detective in #, the entangler in #
		universe_file.seek(0)		
		universe_file.readline() #skip 4 lines to get to actual universes
		universe_file.readline()
		universe_file.readline()
		universe_file.readline()
	
		output_buffer = []
		entangler_subsidiary_buffer = []
		nk_hit_nonentangler_in_some_universe = False
	
		universes_collapsed = [0, 0, 0] #nightkill scum, nightkill entangler, det-guard
	
		#track scum action
		for _ in range(num_universes):
			universe_chunk = qm_shared.parse_universe(universe_file.readline())
			universe = universe_chunk[1]
			universe_to_transform = [*universe]
		
			#order of operations: scum kill goes first.
			thisuni_scum_index = universe.index('A')
			scum_target_index = qm_shared.player_to_pos(player_action_blocs[thisuni_scum_index][scum_index])
			scum_target_role = universe[scum_target_index] #that is, the role of the player who is the NK target
			is_nking_entangler = False
		
			guard_blocking_nk = False
			guard_blocking_det = False
		
			if has_guard_right_now and 'G' in universe:
				thisuni_guard_index = universe.index('G')
				guard_target_index = qm_shared.player_to_pos(player_action_blocs[thisuni_guard_index][guard_index])
				if scum_target_index ==  guard_target_index:
					guard_blocking_nk = True
		
			if has_detective_right_now and 'D' in universe:
				thisuni_det_index = universe.index('D')
				det_target_index = qm_shared.player_to_pos(player_action_blocs[thisuni_det_index][detective_index])
				if has_guard_right_now and guard_target_index ==  det_target_index:
					guard_blocking_det = True

			if scum_target_role in 'DFGTX': #we are assuming the guard cannot guard themself in the overall game rules, but we don't check for it anywhere in this program. You'll need to filter for it before entering actions into this program.
				if guard_blocking_det and (scum_target_role != 'D' or guard_blocking_nk): #that is, if the detective is able to investigate while the guard blocks them, and the detective was not nightkilled...
					#print(f"Universe {universe_chunk} collapses as detective meets guard.") #debug
					universes_collapsed[2] += 1
					continue #...then the universe collapses and we mulligan
				
				nk_hit_nonentangler_in_some_universe = True
				if not guard_blocking_nk:
					universe_to_transform[scum_target_index] = 'X' #mark nightkill (does nothing if player already NKd in this universe)
				output_buffer.append([universe_chunk[0],universe_to_transform]) #copy to out
				continue
	
			if scum_target_role == 'E':
				if guard_blocking_det: #the investigation will always start because scum didn't nk the detective
					#print(f"Universe {universe_chunk} collapses as detective meets guard. (E)") #debug
					universes_collapsed[2] += 1
					continue #this universe collapses, never mind
				elif guard_blocking_nk:
					nk_hit_nonentangler_in_some_universe = True #it's an edge case. There is one universe where the nightkill did not kill the entangler, so that's good enough for quantum immortality!
					output_buffer.append([universe_chunk[0],universe_to_transform]) #add to normal list
					continue
			
				if not nk_hit_nonentangler_in_some_universe:
					#print(f"Universe {universe_chunk} moved to entangler subsidiary list as nightkill hits entangler.")
					universe_to_transform[scum_target_index] = 'X' #mark nightkill (exigent)
					entangler_subsidiary_buffer.append([universe_chunk[0],universe_to_transform])
				else:
					#print(f"Universe {universe_chunk} collapses as nightkill hits entangler.") #debug
					universes_collapsed[1] += 1
				continue
		
			if scum_target_role in 'ABC': #scum targeting other scum - impossible - universe collapses - guard targeting does _not_ affect this because mafia couldn't target other mafia in the first place
				#print(f"Universe {universe_chunk} collapses as scum targets other scum.") #debug - this happens before the other collapse notifs
				universes_collapsed[0] += 1
				continue	
			
			if scum_target_role == 'V':
				print("A scum player tried to target someone voted out. This should have been caught earlier and rejected.")
				exit()
		
			print(f"A scum player targeted someone with an unknown role ({scum_target_role}). Please check that everything is correctly set up.")
			exit()

		if len(output_buffer) == 0:
			if len(entangler_subsidiary_buffer) == 0:
				qm_shared.paradox("nightkill/investigation") #will exit
			output_buffer = entangler_subsidiary_buffer
			print("It is my sad duty to announce that the Entangler has been killed in every surviving universe.")
		else:	
			#print(f"Marking {len(entangler_subsidiary_buffer)} dead-entangler universes as collapsed.")
			universes_collapsed[1] += len(entangler_subsidiary_buffer)
		del entangler_subsidiary_buffer #maybe reclaim memory space
	
		print("Nightkill phase complete. {} universes collapsed in the phase ({} scum target scum, {} entangler immortality, {} detective meets guard).".format(sum(universes_collapsed),*universes_collapsed))
	
		#so now we've done steps 1-3. Now we check for deadness and flip if need be. This is done by [S] Cascade.
		updated_liveness = qm_shared.cascade(output_buffer, player_liveness)

		#we will also need to update liveness again for 100% roles.
		updated_liveness = qm_shared.transform_liveness_roles(output_buffer, updated_liveness)
		qm_shared.close_universe_file()
	
		#we also need to update current_setup.
		# num_players_left = current_setup[0] #aliases
	# 	num_scum_left = current_setup[1]
	# 	has_detective_right_now = current_setup[2]
	# 	has_entangler_right_now = current_setup[3]
	# 	has_follower_right_now = current_setup[4]
	# 	has_guard_right_now = current_setup[5]
		new_setup = [0, num_scum_left, has_detective_right_now, has_entangler_right_now, has_follower_right_now, has_guard_right_now]
		for player in updated_liveness:
			if player[1] == '#': #alive
				new_setup[0] += 1
			elif player[0] == 'D': #dead detective
				new_setup[2] = False
			elif player[0] == 'E': #dead entangler (?!)
				new_setup[3] = False
			elif player[0] == 'F': #dead follower
				new_setup[4] = False
			elif player[0] == 'G': #dead guard
				new_setup[5] = False
			#we won't be checking numbers of scum today, scum's numbers cannot decrease by a nightkill
		assert new_setup[0] <= current_setup[0]
		assert not new_setup[2] or has_detective_right_now
		assert not new_setup[3] or has_entangler_right_now
		assert not new_setup[4] or has_follower_right_now
		assert not new_setup[5] or has_guard_right_now
		num_players_left = new_setup[0]
		has_detective_right_now = new_setup[2]
		has_entangler_right_now = new_setup[3]
		has_follower_right_now = new_setup[4]
		has_guard_right_now = new_setup[5]
		#now, check victory.
		#for a scum victory to be declared, if N scum survive, there must be at most N-1 other players - in every surviving universe.
		#we do not need to check for a draw or town victory at night, as scum can't die here, and both of those conditions occur when the last scum dies. (this works because nothing can stop a vote so scum are never alive in some universes as scum and dead in others as scum)
	
		qm_shared.check_scum_victory(output_buffer, num_scum_left)
		#possible cases: 
			#all scum determinate: "The surviving scum players, #, #, and #, have won.
			#most scum determinate 1 indeterminate 
		player_liveness = updated_liveness #we'll need this for the entangler calculations in a moment
		current_setup = new_setup #and we'll need this for writing the universe file
	# ### NOT ENTANGLER_ONLY BLOCK ENDS HERE
	
	if has_entangler_right_now or entangler_only:
		existing_masonries = []

		if args.night != 0:
			existing_masonries = qm_shared.read_masonry_file(f"masonries-N{args.night}.txt")
		
			#now, reap existing masonries
			qm_shared.close_masonries(existing_masonries, player_liveness, output_buffer)
	
		#now we create new masonries.
		entangler_request_list = [[item[1] == '#', 0, [], 0, qm_shared.get_probability_table_idx(idx), idx] for idx, item in enumerate(player_liveness)]
		#each item in entangler_request_list is a TARGET player. It will have the relevant sort items, starting with:
		# is valid (boolean) - i.e. is a living player.
		# num masonries player is already in (int). - None indicates unfilled
		# num times requested (list so we know who by).
		# num universes player is alive in (int).
		# order in public probability table (transform the index).
		
	
		for idx, entangler_request in enumerate(entangler_requests):
			if entangler_request == '#':
				continue #skip blanks
			if player_liveness[idx][1] != '#':
				continue #
			request_idx = qm_shared.player_to_pos(entangler_request)	
			if not entangler_request_list[request_idx][0]:
				continue #dead players can't be entangled
			entangler_request_list[request_idx][2].append(idx) #note requesting entangler

		#now we need to compute the other two tie breakers: number of masonries currently in, and number of universes currently in.
		#if night == 0, we skip the number-of-universes tiebreaker, as it's a bear to compute AND we don't have access to the universe list.
		for masonry in existing_masonries:
			entangler_request_list[masonry[0]][1] += 1
			entangler_request_list[masonry[1]][1] += 1
		
		if args.night != 0: #universes tiebreaker	
			for universe in output_buffer:
				for idx, player in enumerate(universe[1]):
					if player in 'XV': 
						continue
					entangler_request_list[idx][3] += 1
		#OK, all done. Now we sort the list.
		entangler_request_list = [x for x in entangler_request_list if x[0] and len(x[2]) > 0] #remove invalid option
		entangler_request_list.sort(key=cmp_to_key(compare_masonry_objects))
		max_masonries = min(len(entangler_request_list) // 2, 2)
		
		print(f"Creating up to {max_masonries} {'masonries' if max_masonries != 1 else 'masonry'} with {len(entangler_request_list)} entangler requests, {len(entangler_request_list)} players requested.")
		print(entangler_request_list)
		
		masonries_made = 0
		all_done = False
		while not all_done and len(entangler_request_list) > 1 and (masonries_made < 2 or args.night == 0):
			erl_index_1 = 0 #we manually iterate over pairs so that when we delete the items we get valid iterating combinations later
			erl_index_2 = 1
			
			while not all_done:
				maybe_linking_player_1 = entangler_request_list[erl_index_1][5]
				maybe_linking_player_2 = entangler_request_list[erl_index_2][5]
				masonry_ok = True
				for masonry in existing_masonries:
					if (masonry[0] == maybe_linking_player_1 and masonry[1] == maybe_linking_player_2) or (masonry[0] == maybe_linking_player_2 and masonry[1] == maybe_linking_player_1):
						masonry_ok = False
						break
				if not masonry_ok:
					erl_index_2 += 1
					if erl_index_2 >= len(entangler_request_list):
						erl_index_1 += 1
						erl_index_2 = erl_index_1 + 1
						if erl_index_2 >= len(entangler_request_list):
							#we have tried every combination and we are all out of ideas.
							print("Out of masonry possibilities.")
							all_done = True #will fall out of inner AND outer while
				else: #ok, this masonry is good. do we need to reap an older masonry?
					should_resort = False
					if entangler_request_list[erl_index_1][1] >= 2:
						removing_idx = None
						check_for_opposite_player = None
						#masonry list is assumed to be sorted by round.
						#find older masonry, delete it from masonries list. update entangler_request_list - both ends.
						for idx, masonry in existing_masonries:
							if masonry[0] == maybe_linking_player_1:
								removing_idx = idx
								check_for_opposite_player = masonry[1]
								break
							elif masonry[1] == maybe_linking_player_1:
								removing_idx = idx
								check_for_opposite_player = masonry[0]
								break
						if removing_idx is not None:
							entangler_request_list[erl_index_1][1] -= 1
							should_resort = True #note this for sorting but don't sort yet.
							for item in entangler_request_list:
								if item[5] == check_for_opposite_player:
									assert item[1] > 0
									item[1] -= 1 #mark them down as in one less masonry
							print(f"Closing masonry between {player_names[maybe_linking_player_1]} and {player_names[check_for_opposite_player]}, as it'll be bumped by the new masonry:") #also print and say it closed
							del existing_masonries[removing_idx]
					if entangler_request_list[erl_index_2][1] >= 2:
						#same as above
						removing_idx = None
						check_for_opposite_player = None
						for idx, masonry in existing_masonries:
							if masonry[0] == maybe_linking_player_2:
								removing_idx = idx
								check_for_opposite_player = masonry[1]
								break
							elif masonry[1] == maybe_linking_player_2:
								removing_idx = idx
								check_for_opposite_player = masonry[0]
								break
						if removing_idx is not None:
							entangler_request_list[erl_index_2][1] -= 1
							should_resort = True 
							for item in entangler_request_list:
								if item[5] == check_for_opposite_player:
									assert item[1] > 0
									item[1] -= 1
							print(f"Closing masonry between {player_names[maybe_linking_player_2]} and {player_names[check_for_opposite_player]}, as it'll be bumped by the new masonry:")
							del existing_masonries[removing_idx]
						
					#now make the masonry.
					print(f"Making a masonry between {player_names[maybe_linking_player_1]} and {player_names[maybe_linking_player_2]}.")
					existing_masonries.append([maybe_linking_player_1, maybe_linking_player_2, args.night, entangler_request_list[erl_index_1][2], entangler_request_list[erl_index_2][2]])
					masonries_made += 1
					del entangler_request_list[erl_index_2] #DELETE our bonded pair members from entangler_request_list. 
					del entangler_request_list[erl_index_1] #(in reverse so as not to mess up indexes.)
					if should_resort: #if we needed to sort above, now sort.
						entangler_request_list.sort(key=cmp_to_key(compare_masonry_objects))
					break #breaks out of inner while			
	
	#END OF MASONRY BLOCK
	
	#write output
	if has_entangler_right_now or entangler_only:
		print("Writing masonry file...")
		qm_shared.write_masonry_file(existing_masonries, f"masonries-D{args.night+1}.txt")

	if not entangler_only:
		print(f"Writing {len(output_buffer)} universe(s) to universe file...")
		qm_shared.write_universe_file(output_buffer,  f"universes-D{args.night+1}.txt", player_liveness, current_setup, args.actions)
	else:
		print(f"Writing supplementary actions file.")
		with open("actions-D1.txt", 'x') as actionfile:
			actionfile.write(args.actions)
		
		
		
		
		
	print("All done!")	
	print(f"*** NEXT (after sending DMs): RUN DAY.PY FOR DAY {args.night+1} ***")
	
	
	#for later - if a NK would kill an entangler, they can't have been the entangler, so mark those universes as contradictory (collapse them).
#if collapsing would remove ALL universes, plan B: mark the target(s) as 'dead' in those universes.
#if this leads to any 100% deaths, scan through the universes and select one where none of the 100% dead targets are the entangler! If this is possible, collapse all universes where the 100% dead person is the Entangler and go with the rest. If this is not possible, pick a universe at random and flip that person as the entangler ig 

def compare_masonry_objects(masonry_1, masonry_2): #returns -1 if a < b in ascending sort order (so a => b). 0 if ==. +1 if a > b (so b => a). The classic is A-B.
	masonry_compare = masonry_1[1] - masonry_2[1] #number of existing masonries, FEWEST to MOST 
	if masonry_compare != 0:
		return masonry_compare
	requests_compare = len(masonry_2[2]) - len(masonry_1[2]) #number of requests, MOST to FEWEST [reverse]
	if requests_compare != 0:
		return requests_compare
	universes_compare = masonry_1[3] - masonry_2[3] #number of universes, FEWEST to MOST
	if universes_compare != 0:
		return universes_compare
	return masonry_1[4] - masonry_2[4] #public probability table compare, FEWEST to MOST - cannot tie

if __name__ == "__main__":
	night()