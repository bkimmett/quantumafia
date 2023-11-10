#!/usr/bin/env python3

import itertools
from sys import exit
from math import factorial, log10, ceil
import qm_shared


### FUNCTIONS

def gen_universe_as_list(base_list, packed_universe, power_roles):
	universe_list = base_list[:]
	for power_role_id, player_id in enumerate(packed_universe): #index, item
		universe_list[player_id] = power_roles[power_role_id] #so if players 3, 6, 2 are set to be the first three power roles, slot [3] in universe_list would be set to power_roles[0], and so on.
	return universe_list


def setup():
	#QUANTUMAFIA SETUP
		
	game_setup, _, _ = qm_shared.read_game_info(0, True) #arguments aren't important
	#game_setup is # players, # mafia, power role T/Fs
	num_players = game_setup[0] #aliases
	num_scum = game_setup[1]
	has_detective = game_setup[2]
	has_entangler = game_setup[3]
	has_follower = game_setup[4]
	has_guard = game_setup[5]
	
	input("This will set up the universes for Quantum Mafia. The resulting universe file will be a VERY LARGE text file (gigabytes large). Press ENTER to continue.")
	
	try:
		with open("universes-D1.txt", 'x') as universelist:
			powerroles = 'ABC'[0:min(3,num_scum)]  \
				+ ('D' if has_detective else '') 	\
				+ ('E' if has_entangler else '') 	\
				+ ('F' if has_follower else '') 	\
				+ ('G' if has_guard else '') 		\
				+ ''.join([chr(72+x) for x in range(num_scum-3)]) #HIJKetc
			
			print("Creating permutations...")
			possible_universes_packed = itertools.permutations(range(num_players),len(powerroles))
			
			expected_universes = factorial(num_players)//factorial(num_players-len(powerroles))
			print("Ready to create {} universes...".format(expected_universes))
			num_digits = ceil(log10(expected_universes))
			universe_format = "{:0"+str(num_digits)+"}-{}"
			#with this, we pick players for the power roles - every possible permutation of players, in fact.
			universe_base = ['T' for _ in range(num_players)]
			universes = (universe_format.format(idx, "".join(gen_universe_as_list(universe_base, packed_universe, powerroles))) for idx, packed_universe in enumerate(possible_universes_packed))
			
			print("{} universes created. Writing to disk...".format(expected_universes))
			universelist.write("{}-{}-{}{}{}{}\n{}\n{}\n\n".format(
				num_players, num_scum, 			#initial state
				(1 if has_detective else 0), (1 if has_entangler else 0), (1 if has_follower else 0), (1 if has_guard else 0),
				"".join("##" for _ in range(num_players)), #player global liveness - format = player role [# = indeterminate, A = scum, DEFG = role, T = town] + player liveness [# = alive in some universe X = dead in every universe V = voted out in every universe]
				expected_universes #len(universes) #number of universes
				#and a blank line for the last night's action string.
				))
			qm_shared.write_lines_to_file(universelist, universes)
			
			print("Day 1 Universe file saved.")
			
			#if expected_universes != len(possible_universes_packed):
			#	print("WARNING - An unexpected number of universes was created. This may indicate a coding error. Proceed at your own risk!")
		
	except FileExistsError:
		print("Error - the starting universe file, universes-D1.txt, already exists. I won't overwrite this file, in case you have a game in progress. If you want to start a new game, delete these files then try running setup again.")
		exit()
	
	if has_entangler:
		print("*** NEXT: RUN NIGHT.PY FOR NIGHT 0 ***")
	else:
		print("*** NEXT: RUN DAY.PY FOR DAY 1 ***")

if __name__ == "__main__":
	setup()