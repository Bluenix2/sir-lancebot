from pathlib import Path
from random import choice

from discord import Color, Embed, File
from discord.ext import commands

from bot.bot import Bot
from asyncio import TimeoutError


class Hangman(commands.Cog):
    """
    Cog for the Hangman game.

    Hangman is a classic game where the user tries to guess a word, with a limited amount of tries.
    """

    def __init__(self, bot: Bot):
        self.bot = bot
        with Path("bot/resources/evergreen/top_1000_used_words.txt").resolve().open(mode="r", encoding="utf-8") as file:
            self.all_words = list(map(lambda line: line.strip('\n'), file.readlines()))

    @commands.command()
    async def hangman(self, ctx: commands.Context, mode: str = 'g',
                      min_length: str = '0', max_length: str = '25',
                      min_unique_letters: str = '0', max_unique_letters: str = '25') -> None:
        """
        Starts the hangman game.
        """

        # filtering the list of all words depending on the configuration
        filtered_words = list(filter(lambda x: int(min_length) < len(x) < int(max_length)
                                     and int(min_unique_letters) < len(set(x)) < int(max_unique_letters),
                                     self.all_words))

        # defining a list of images that will be used for the game to represent the 'hung man'
        images = [f'hangman{num}.png' for num in range(0, 7)]

        # a dictionary mapping the images of the 'hung man' to the number of tries it corresponds to
        mapping_of_images = {}

        for image_name, tries_equal_to in zip(images, range(6, 0, -1)):
            mapping_of_images[tries_equal_to] = File(f"bot/resources/evergreen/hangman/{image_name}",
                                                     filename=image_name)

        word = choice(filtered_words)
        user_guess = '_' * len(word)
        tries = 6
        hangman_embed = Embed(title="Hangman", color=Color.blurple())
        hangman_embed.set_image(url=f"attachment://{mapping_of_images[tries].filename}")
        hangman_embed.add_field(name=f"The word is `{user_guess}`", value="Guess the word by sending a "
                                                                          "message with the letter!", inline=False)
        original_message = await ctx.send(file=mapping_of_images[tries], embed=hangman_embed)

        while user_guess != word:
            # unfortunately, the bot needs to generate the dictionary every time to avoid an operation on a closed file
            for image_name, tries_equal_to in zip(images, range(6, 0, -1)):
                mapping_of_images[tries_equal_to] = File(f"bot/resources/evergreen/hangman/{image_name}",
                                                         filename=image_name)

            try:
                message = await self.bot.wait_for(event="message", timeout=30.0,
                                                  check=lambda msg: msg.author != self.bot)

                if len(message.content) > 1:
                    continue
                elif message.content in word:
                    positions = [idx for idx, letter in enumerate(word) if letter == message.content]
                    user_guess = ''.join([message.content if index in positions else dash
                                          for index, dash in enumerate(user_guess)])
                elif tries - 1 <= 0:
                    await original_message.delete()
                    losing_embed = Embed(title="You lost.", description=f"The word was `{word}`.", color=Color.red())
                    await ctx.send(embed=losing_embed)
                    return
                else:
                    tries -= 1

                hangman_embed.clear_fields()
                hangman_embed.set_image(url=f"attachment://{mapping_of_images[tries].filename}")
                hangman_embed.add_field(name=f"The word is `{user_guess}`", value="Guess the word by sending a "
                                                                                  "message with the letter!",
                                        inline=False)
                await original_message.delete()
                original_message = await ctx.send(file=mapping_of_images[tries], embed=hangman_embed)
            except TimeoutError:
                return
        else:
            win_embed = Embed(title="You won!", color=Color.green())
            await original_message.delete()
            await ctx.send(embed=win_embed)


def setup(bot: Bot) -> None:
    """Setting up the Hangman cog."""
    bot.add_cog(Hangman(bot))
