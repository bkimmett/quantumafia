#!/usr/bin/env python3

import argparse, random
from sys import exit

### FUNCTIONS	
def player_marker(num): #0 = A, 1 = B...
	return chr(65+num)

def setup():
	#QUANTUMAFIA SETUP 1 - INITIAL SETUP
	#to change starting parameters, change this
	num_players = 8 #19 
	num_mafia = 2 #3 #use 'abc' by default. more will use ABCHIJ ig? [HIJKLMNOPQRS]
	has_detective = True
	has_entangler = True
	has_follower = True
	has_guard = True

	if num_players > 26: #sanity check
		print("Error - this program isn't built for that many players.")
		exit()

	if num_mafia > 15:
		print("Error - this program isn't built for that many mafia members.")
		exit()
	
	if num_mafia < 1:
		print("Error - this isn't Gnosia (the video game). Set at least one mafia player.")
		exit()

	parser = argparse.ArgumentParser(
						prog='Quantumafia Setup',
						description='This sets up a match of Quantumafia.')
					
	parser.add_argument('seed', type=int, help="Random seed. This allows for repeatable randomness in games. A random number will be used if none is supplied.", default=None, nargs='?')
	args = parser.parse_args()
	seed = args.seed

	if seed is None:
		seed = random.randint(100000000000000, 999999999999999-num_players)
	
	random_source = random.Random(seed)
	
	player_sequence = [x for x in range(num_players)]
	random_source.shuffle(player_sequence)

	try:
		with open("gameinfo.txt", 'x') as gameinfo:
			gameinfo.write("{}-{}-{}{}{}{}\n{}\n{}".format(
				num_players, num_mafia, 			#initial state
				(1 if has_detective else 0), (1 if has_entangler else 0), (1 if has_follower else 0), (1 if has_guard else 0),
				seed, \
				"".join([player_marker(x) for x in player_sequence]), #player shuffling for board
				))  #65 is the code point for unicode 'A', so the sequence goes ABCDEFGHIJ... but shuffled
		
		with open("players.txt", 'x') as playerlist:
			with open("codewords.txt", 'x') as codewordlist:
				for num in range(num_players):
					playerlist.write("{}: PLAYER{}_NAME\n".format(player_marker(num),num+1))
					codewordlist.write("CWORD{}\n".format(num+1))
				playerlist.write("\nThe first player in the list will be referred to as 'A' in universe files and command line commands. The second player in the list will be referred to as 'B', the third will be referred to as 'C', and so on.\nNote: Don't remove the 'A: ', 'B: '... prefixes (including the spaces) from the lines. QM will remove those automatically.")
		
	except FileExistsError:
		print("Error - one or more of [A] the player list file, players.txt, [B] the codeword list file, codewords.txt, or [C] the game setup file, gameinfo.txt, already exist. I won't overwrite these files, in case you have a game in progress. If you want to start a new game, delete these files then try running setup again.")
		exit()


	print("The player list and codeword list files have been generated in this folder (players.txt and codewords.txt). Please open the player list file and replace the PLAYER_NAME placeholders with the names of the players; in the codewords file, please replace the CWORD placeholders with the codewords that will be used on the public probability table, in the order they will be displayed.\n\n")

	input("When you are done editing the files, save them and press ENTER.")


	with open("players.txt", 'r') as playerlist:
		player_names = [playerlist.readline() for _ in range(num_players)]
		player_names_shuffled = [player_names[idx] for idx in player_sequence]
	
		print("Private info - the public probability table will be displayed with players in the following order:")
		for name in player_names_shuffled:
			print(name, end='')
		print()
		print("You should probably save this info, but don't post it publicly.")
	
	print("*** NEXT: RUN UNIVERSE_SETUP.PY ***")
	print("Note: If you are rerunning this file after running universe_setup.py once already, you only need to rerun universe_setup.py if the number of players, number of mafia, or distribution of other power roles has changed.")

if __name__ == "__main__":
	setup()