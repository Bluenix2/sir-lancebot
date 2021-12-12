import asyncio
from json import JSONDecodeError, loads
from random import choice
from typing import Optional

from discord import Embed
from discord.colour import Color
from discord.ext import commands

from bot.bot import Bot
from bot.constants import Colours, NEGATIVE_REPLIES, POSITIVE_REPLIES, Roles

from ._game import TriviaNightGame
from ._questions import QuestionView, Questions
from ._scoreboard import Scoreboard, ScoreboardView

# The ID you see below is the Events Lead role ID
TRIVIA_NIGHT_ROLES = (Roles.admin, 78361735739998228)


class TriviaNightCog(commands.Cog):
    """Cog for the Python Trivia Night event."""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.game: Optional[TriviaNightGame] = None

    @commands.group(aliases=["tn"], invoke_without_command=True)
    async def trivianight(self, ctx: commands.Context) -> None:
        """
        The command group for the Python Discord Trivia Night.

        If invoked without a subcommand (i.e. simply .trivianight), it will explain what the Trivia Night event is.
        """
        cog_description = Embed(
            title="What is .trivianight?",
            description=(
                "This 'cog' is for the Python Discord's TriviaNight (date tentative)! Compete against other"
                " players in a trivia about Python!"
            ),
            color=Colours.soft_green
        )
        await ctx.send(embed=cog_description)

    @trivianight.command()
    @commands.has_any_role(*TRIVIA_NIGHT_ROLES)
    async def load(self, ctx: commands.Context, *, to_load: Optional[str]) -> None:
        """
        Loads a JSON file from the provided attachment or argument.

        The JSON provided is formatted where it is a list of dictionaries, each dictionary containing the keys below:
        - number: int (represents the current question #)
        - description: str (represents the question itself)
        - answers: list[str] (represents the different answers possible, must be a length of 4)
        - correct: str (represents the correct answer in terms of what the correct answer is in `answers`
        - time: Optional[int] (represents the timer for the question and how long it should run, default is 10)
        - points: Optional[int] (represents how many points are awarded for each question, default is 10)

        The load command accepts three different ways of loading in a JSON:
        - an attachment of the JSON file
        - a message link to the attachment/JSON
        - reading the JSON itself via a codeblock or plain text
        """
        if self.game is not None:
            await ctx.send(embed=Embed(
                title=choice(NEGATIVE_REPLIES),
                description="There is already a trivia night running!",
                color=Colours.soft_red
            ))
            return

        if ctx.message.attachments:
            json_text = (await ctx.message.attachments[0].read()).decode("utf8")
        elif not to_load:
            raise commands.BadArgument("You didn't attach an attachment nor link a message!")
        elif to_load.startswith("https://discord.com/channels") or \
                to_load.startswith("https://discordapp.com/channels"):
            channel_id, message_id = to_load.split("/")[-2:]
            channel = await ctx.guild.fetch_channel(int(channel_id))
            message = await channel.fetch_message(int(message_id))
            if message.attachments:
                json_text = (await message.attachments[0].read()).decode("utf8")
            else:
                json_text = message.content.replace("```", "").replace("json", "").replace("\n", "")
        else:
            json_text = to_load.replace("```", "").replace("json", "").replace("\n", "")

        try:
            serialized_json = loads(json_text)
        except JSONDecodeError:
            raise commands.BadArgument("Invalid JSON")

        self.game = TriviaNightGame(serialized_json)

        success_embed = Embed(
            title=choice(POSITIVE_REPLIES),
            description="The JSON was loaded successfully!",
            color=Colours.soft_green
        )
        await ctx.send(embed=success_embed)

    @trivianight.command(aliases=('next',))
    @commands.has_any_role(*TRIVIA_NIGHT_ROLES)
    async def question(self, ctx: commands.Context, question_number: str = None) -> None:
        """
        Gets a random question from the unanswered question list and lets the user(s) choose the answer.

        This command will continuously count down until the time limit of the question is exhausted.
        However, if `.trivianight stop` is invoked, the counting down is interrupted to show the final results.
        """
        if self.game is None:
            await ctx.send(embed=Embed(
                title=choice(NEGATIVE_REPLIES),
                description="There is no trivia night running!",
                color=Colours.soft_red
            ))
            return

        if self.game.current_question is not None:
            error_embed = Embed(
                title=choice(NEGATIVE_REPLIES),
                description="There is already an ongoing question!",
                color=Colours.soft_red
            )
            await ctx.send(embed=error_embed)
            return

        next_question = self.game.next_question(question_number)

        question_view = QuestionView(next_question)
        question_embed = question_view.create_embed()

        next_question.start()
        message = await ctx.send(embed=question_embed, view=question_view)

        # Exponentially sleep less and less until the time limit is reached
        percentage = 1
        while True:
            percentage *= 0.5
            duration = next_question.time * percentage

            await asyncio.sleep(duration)
            if int(duration) > 1:
                # It is quite ugly to display decimals, the delay for requests to reach Discord
                # cause sub-second accuracy to be quite pointless.
                await ctx.send(f"{int(duration)}s remaining...")
            else:
                # Since each time we divide the percentage by 2 and sleep one half of the halves (then sleep a
                # half, of that half) we must sleep both halves at the end.
                await asyncio.sleep(duration)
                break

        await ctx.send(embed=question_view.end_question())
        await message.edit(embed=question_embed, view=None)
        question_view.stop()

    @trivianight.command()
    @commands.has_any_role(*TRIVIA_NIGHT_ROLES)
    async def list(self, ctx: commands.Context) -> None:
        """
        Display all the questions left in the question bank.

        Questions are displayed in the following format:
        Q(number): Question description | :white_check_mark: if the question was used otherwise :x:.
        """
        question_list = self.questions.list_questions()
        if isinstance(question_list, Embed):
            await ctx.send(embed=question_list)
            return

        await ctx.send(question_list)

    @trivianight.command()
    @commands.has_any_role(*TRIVIA_NIGHT_ROLES)
    async def stop(self, ctx: commands.Context) -> None:
        """
        End the ongoing question to show the correct question.

        This command should be used if the question should be ended early or if the time limit fails
        """
        if self.questions.view.active_question is False:
            error_embed = Embed(
                title=choice(NEGATIVE_REPLIES),
                description="There is not an ongoing question to stop!",
                color=Colours.soft_red
            )
            await ctx.send(embed=error_embed)
            return

        self.questions.view.active_question = False

    @trivianight.command()
    @commands.has_any_role(*TRIVIA_NIGHT_ROLES)
    async def end(self, ctx: commands.Context) -> None:
        """
        Ends the trivia night event and displays the scoreboard view.

        The scoreboard view consists of the two scoreboards with the 30 players who got the highest points and the
        30 players who had the fastest average response time to a question where they got the question right.

        The scoreboard view also has a button where the user can see their own rank, points and average speed if they
        didn't make it onto the leaderboard.
        """
        if self.game is None:
            await ctx.send(embed=Embed(
                title=choice(NEGATIVE_REPLIES),
                description="There is no trivia night running!",
                color=Colours.soft_red
            ))
            return

        if self.game.current_question is not None:
            error_embed = Embed(
                title=choice(NEGATIVE_REPLIES),
                description="You can't end the event while a question is ongoing!",
                color=Colours.soft_red
            )
            await ctx.send(embed=error_embed)
            return

        scoreboard_embed, scoreboard_view = await self.scoreboard.display()
        await ctx.send(embed=scoreboard_embed, view=scoreboard_view)
        self.game = None


def setup(bot: Bot) -> None:
    """Load the TriviaNight cog."""
    bot.add_cog(TriviaNightCog(bot))
