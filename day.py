#!/usr/bin/env python3

import argparse, random, qm_shared
from sys import exit

#DAY PRECESSION

def day():
	parser = argparse.ArgumentParser(
						prog='Quantumafia Day Processor',
						description='This processes the end-of-day transition in a match of Quantumafia.')
					
	parser.add_argument('day', type=int, help="Indicates which game day (1, 2, 3...) is to be transitioned.")
	parser.add_argument('vote', help="One or more letters, from A, B, C... which indicates which player was voted out. Separate successive letters by spaces if more than one. If more than one player is supplied one of them will be picked randomly." nargs='+' type=qm_shared.single_letter)
	args = parser.parse_args()

	#this block is the same as night's block
	game_setup, random_source, _ = qm_shared.read_game_info(args.day, False)
	#game_setup is # players, # mafia, power role T/Fs
	num_players = game_setup[0] #aliases
	num_scum = game_setup[1]
	has_detective = game_setup[2]
	has_entangler = game_setup[3]
	has_follower = game_setup[4]
	has_guard = game_setup[5]
	
	# we also want to read player liveness and current setup state from universes file
	current_setup, player_liveness, num_universes = qm_shared.read_current_info(args.day, True)
	
	num_players_left = current_setup[0] #aliases
	num_scum_left = current_setup[1]
	has_detective_right_now = current_setup[2]
	has_entangler_right_now = current_setup[3]
	has_follower_right_now = current_setup[4]
	has_guard_right_now = current_setup[5]
	#remember that liveness is two characters: first is role if 100%, second is liveness (# alive, X 100% dead, V voted out)
	
	player_names = qm_shared.read_player_names()
	
	if not all(char.isalpha() and char.isascii() and qm_shared.player_to_pos(char) < num_players for char in args.vote):
		print(f"Invalid character in votes. Accepts only A-{qm_shared.pos_to_player(num_players-1)} for targets, # for 'no target', and - as a separator.")
		exit()
	#get vote (to uppercase). complain if vote is nonsense per num_players.
	#check vs global state. if voted player is X or V in every universe, complain.
	if any(player_liveness[qm_shared.player_to_pos(char)][1] != '#' for char in args.vote):
		print("One or more targeted players have been voted out or are 100% dead already. Remove them from the vote list and try again.")
	
	if len(args.vote) > 1:
		vote = random_source.choice(args.vote)
		print("More than one vote candidate. Choosing one randomly...")
	else:
		vote = args.vote[0]
		
		
	print(f"Voting out {player_names[vote]}.")
	vote = qm_shared.player_to_pos(vote)
	
	output_buffer = []
	entangler_subsidiary_buffer = []
	vote_hit_nonentangler_in_some_universe = False

	universes_collapsed = [0, 0] #already dead, vote entangler

	#track scum action
	for _ in range(num_universes):
		universe_chunk = qm_shared.parse_universe(universe_file.readline())
		universe = universe_chunk[1]
		universe_to_transform = [*universe]
		
		voted_player_role = universe[vote]
	
		if voted_player_role == 'X':
			universes_collapsed[0] += 1
			continue
	
		universe_to_transform[vote] = 'V' #mark dead
	
		if voted_player_role == 'E':
			if not vote_hit_nonentangler_in_some_universe:
				entangler_subsidiary_buffer.append([universe_chunk[0],universe_to_transform])
			else:
				universes_collapsed[0] += 1
				continue
		elif voted_player_role in 'ABCDFGT':
			vote_hit_nonentangler_in_some_universe = True	
			output_buffer.append([universe_chunk[0],universe_to_transform])
			continue
		else:
			print(f"The voted target player was found with an unknown role ({voted_player_role}). Giving up.")
			exit()


	if len(output_buffer) == 0:
		if len(entangler_subsidiary_buffer) == 0:
			qm_shared.paradox("voting") #will exit
		output_buffer = entangler_subsidiary_buffer
		print("It is my sad duty to announce that the Entangler has been killed in every surviving universe.")
	else:
		universes_collapsed[1] += len(entangler_subsidiary_buffer)
	del entangler_subsidiary_buffer #maybe reclaim memory space

	print("Voting phase complete. {} universes collapsed in the phase ({} target already dead, {} entangler ).".format(sum(universes_collapsed),*universes_collapsed))
		
		
	#update liveness and state, and cascade. pretty much the same as for Night.
	
	updated_liveness = qm_shared.cascade(output_buffer, player_liveness)
	qm_shared.close_universe_file()
	updated_liveness = qm_shared.transform_liveness_roles(output_buffer, updated_liveness)

	#we also need to update current_setup.
	new_setup = [0, num_scum, has_detective_right_now, has_entangler_right_now, has_follower_right_now, has_guard_right_now]
	for player in updated_liveness:
		if player[1] == '#': #alive
			new_setup[0] += 1
		elif player[0] in 'ABC': #dead detective
			new_setup[1] -= 1
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
	#scum_died = num_scum_left != new_setup[1]
	num_scum_left = new_setup[1]
	has_detective_right_now = new_setup[2]
	has_entangler_right_now = new_setup[3]
	has_follower_right_now = new_setup[4]
	has_guard_right_now = new_setup[5]	
		
	
	#note that we set scum_died. We will use this to check for victory, and we _may_ use this to promote scum.

	if num_scum_left == 0:
		#check for draw or town victory
		always_alive = [True for _ in updated_liveness]
		sometimes_alive = [False for _ in updated_liveness]
		min_living_players = num_players_left
		max_living_players = 0
		
		for universe in output_buffer:
			players_in_this_univ = 0
			for idx, player in enumerate(universe[1]):
				if player not in 'XV':
					sometimes_alive[idx] = True
					players_in_this_univ += 1
				else:
					always_alive[idx] = False
			min_living_players = min(min_living_players, players_in_this_univ)
			max_living_players = max(max_living_players, players_in_this_univ)

		write_final_universe_file(output_buffer, "universes-final.txt")
		if not any(sometimes_alive):
			print("*** DRAW ***")
			print("Everybody dies. The game is over!")
			exit()
		else:
			print("*** TOWN VICTORY ***")
			always_alive_indexes = [idx for idx, item in enumerate(always_alive) if item]
			sometimes_alive_indexes = [idx for idx, item in enumerate(sometimes_alive) if item and not always_alive[idx]]
			min_variable_living_players = min_living_players - len(always_alive_indexes)
			max_variable_living_players = max_living_players - len(always_alive_indexes)
			always_alive_names = [get_player_name(idx) for idx in always_scum_indexes]
			sometimes_alive_names = [get_player_name(idx) for idx in always_scum_indexes]
			if max_variable_living_players == 0:
				print(f'The surviving town player{"s" if num_players_left > 1 else ""}, {qm_shared.oxford_comma(always_alive_names, "and")}, {"have" if num_players_left > 1 else "has"} won.')
			else:		
				print(f'The surviving town player{"s" if num_players_left > 1 else ""}, {", ".join(always_alive_names)}{" and " if len(always_alive_names) > 0 else ""}{"{}".format(max_variable_living_players) if max_variable_living_players == min_variable_living_players else "{}-{}".format(min_variable_living_players,max_variable_living_players)} of {qm_shared.oxford_comma(sometimes_alive_names, "or")}, {"have" if num_players_left > 1 else "has"} won.')
			exit()
	else:
		#check for scum victory (if scum didn't die, we can't have a TOWN victory or DRAW because one scum is still alive.)
		qm_shared.check_scum_victory(output_buffer) #may exit
		
	#now maybe promote scum	
	for universe in output_buffer:
		if 'A' not in universe[1]: #no alpha scum
			try:
				c_index = universe[1].index('C')
			except ValueError:
				c_index = None
			try:
				b_index = universe[1].index('B')
			except ValueError:
				b_index = None
			if b_index is None:
				universe[1][c_index] = 'A'
			else:
				universe[1][b_index] = 'A'
				if c_index is not None:
					universe[1][c_index] = 'B'
	
	#possibly, reap masonries at this point
	
	if has_entangler_right_now:
		existing_masonries = qm_shared.read_masonry_file(f"masonries-D{args.day}.txt")
		#now, reap existing masonries
		qm_shared.close_masonries(existing_masonries, updated_liveness, output_buffer)
			
		#now, write masonry file
		print("Writing masonry file...")
		qm_shared.write_masonry_file(existing_masonries, f"masonries-N{args.day}.txt")
		
	#now, write output universes
	qm_shared.write_universe_file(output_buffer,  f"universes-N{args.day}.txt", updated_liveness, new_setup, "")
	
	print("All done!")	
	print(f"*** NEXT (after sending DMs): RUN NIGHT.PY FOR NIGHT {args.day} ***")
	
	#go through all universes. In universes where player is X, do nothing. In universes where player is E, add to E-buffer *UNLESS* we have seen our player as alive and non-E in at least one universe (we can throw out E-buffer in this case). Also skip if there is no entangler in the active setup.
	#In universes where player is alive, mark as V and add to output buffer.
	#If output buffer is empty when we're done, replace with E-buffer, announce Entangler death. If BOTH buffers are empty, complain.
	
	#update global state to 'V' for target player.
	
	#AT THIS POINT, pick a random universe from the buffer. That universe ID (get from global D1)_ will be that player's flip. DISPLAY THIS FLIP!
		#note to self: if fns shared among files, add a support module file.
		
	#now, run through the buffer again. Any CONTRADICTORY UNIVERSES are removed. That is, ones where the player doesn't match their flip.
	
		#Additionally: if the player was scum in their flip, promote scum in all remaining universes.
	
	#once the dust settles, we need to check if this [S] Cascaded. Did anyone else bite it?
	
	#deathness check: using global state, figure out who's alive. Create a list like [False, True, True, True, False] where the position of the false is the index in the universe string of each living(?) player's letter. (False indicates an indeterminate state here. True at the start means dead. True later means alive.)
		#For each universe in the buffer, check the indices of each not-entirely-living player (boil false-list to indexes with list comprehension).
		#For each player found to be living in *some* universe, change that index in the list to True.
		#so fewer checks are done in succeeding universes.
		#If the dust settles and there is still a 'false' after running through the entire buffer...
		#...then that player (or players) must be dead!
		#now we get to the absolutely nasty part. Pick one of the remaining universes in the buffer. This will be the flip (or CHAINED FLIP if more than one player) for the newly dead players.
		
		#get their state from the global list and read off the NEW FLIPs. DISPLAY FLIP(S).
			#if a flip is a power role, edit the current game state!! (the numeric, not the liveness)
		
		#then, we need to (time-consuming!) scan the buffer and global list. Remove, from the buffer, any CONTRADICTORY UNIVERSES. (can we outsource this to filter()?) 			
		#yeah we'll definitely need a GET PRISTINE UNIVERSE FROM GLOBAL LIST BY ID fn here.
		#use the same routine as we did for the earlier cascade above.
		
		#oh, and set global state to 'X', ofc.
		
		#now for the nasty part: if ANY player was found dead here, LOOP AROUND AND DO THIS WHOLE THING AGAIN! We might have more recursive deaths.
		
#fns: COLLAPSE (maybe) and CASCADE
	#COLLAPSE filters a buffer by comparing that certain player(s) are set to certain values in their current string. handle entangler case as well
		#maybe we custom do COLLAPSE. Night will not use it as night goes through each universe one by one processing night actions and enumerating surviving universes.
			#COLLAPSE can also filter for a temporal paradox, and the game will handle that as is.
	#CASCADE filters a buffer by comparing that certain player(s) are set to certain values in their ORIGINAL string [from raw universe file - mmap this]. We will need to use this with deathness check in night() too.
		
		
	#check for victory at this point. #A DRAW CAN OCCUR - this is all dead in every universe, after other possibilities collapse from flip.
	#CHECK FOR TOWN OR SCUM VICTORY - town victory = all scums found. scum victory = scum controls the vote in *EVERY* universe (count remaining universes in buffer, stop on first non-victory)
		
	#if we end up with an empty buffer at this point, COMPLAIN about a TEMPORAL PARADOX. else write night universe file.
			
	#an-y-way: Track all definitely voted out / dead players. We'll use this for the masonry check.		
			
	
			
	#masonry check: open masonry file for Day. Close any masonries with the voted-out player or otherwise def-dead players.
	#also remove voted player / dead players from entanglers. Close any masonries this cascades to. 
	#write masonry file for Night.


if __name__ == "__main__":
	day()