import asyncio
from json import loads
from random import choice

from discord import Embed
from discord.ext import commands

from bot.bot import Bot
from bot.constants import Colours, POSITIVE_REPLIES

from ._questions import QuestionView, Questions
from ._scoreboard import Scoreboard, ScoreboardView


class TriviaNight(commands.Cog):
    """Cog for the Python Trivia Night event."""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.scoreboard = Scoreboard()
        self.questions = Questions(self.scoreboard)

    @staticmethod
    def unicodeify(text: str) -> str:
        """Takes `text` and adds zero-width spaces to prevent copy and pasting the question."""
        return "".join(
            f"{letter}\u200b" if letter not in ('\n', '\t', '`', 'p', 'y') else letter
            for idx, letter in enumerate(text)
        )

    @commands.group(aliases=["tn"], invoke_without_command=True)
    async def trivianight(self, ctx: commands.Context) -> None:
        """No-op subcommand group for organizing different commands."""
        if ctx.invoked_subcommand is None:
            cog_description = Embed(
                title="What is .trivianight?",
                description=(
                    "This 'cog' is for the Python Discord's TriviaNight (date tentative)! Compete against other"
                    "players in a trivia about Python!"
                ),
                color=Colours.soft_green
            )
            await ctx.send(embed=cog_description)

    @trivianight.command()
    async def load(self, ctx: commands.Context) -> None:
        """Load the JSON file provided into the questions."""
        json_text = (await ctx.message.attachments[0].read()).decode("utf8")
        serialized_json = loads(json_text)
        for idx, question in enumerate(serialized_json):
            serialized_json[idx] = {**question, **{"description": self.unicodeify(question["description"])}}
        self.questions.view = QuestionView()
        self.scoreboard.view = ScoreboardView(self.bot)
        self.questions.set_questions(serialized_json)
        success_embed = Embed(
            title=choice(POSITIVE_REPLIES),
            description="The JSON was loaded successfully!",
            color=Colours.soft_green
        )
        await ctx.send(embed=success_embed)

    @trivianight.command()
    async def reset(self, ctx: commands.Context) -> None:
        """Resets previous questions and scoreboards."""
        self.scoreboard.view = ScoreboardView(self.bot)
        for question in self.questions.questions:
            del question["visited"]

        success_embed = Embed(
            title=choice(POSITIVE_REPLIES),
            description="The scoreboards were reset and questions marked unvisited!",
            color=Colours.soft_green
        )
        await ctx.send(embed=success_embed)

    @trivianight.command()
    async def next(self, ctx: commands.Context) -> None:
        """Gets a random question from the unanswered question list and lets user choose the answer."""
        next_question = self.questions.next_question()
        if isinstance(next_question, Embed):
            await ctx.send(embed=next_question)
            return

        (question_embed, time_limit), question_view = self.questions.current_question()
        await ctx.send(embed=question_embed, view=question_view)

        for time_remaining in range(time_limit - 1, -1, -1):
            await asyncio.sleep(1)
            if time_remaining % 5 == 0:
                await ctx.send(f"{time_remaining}s remaining")

        await ctx.send(embed=self.questions.end_question())

    @trivianight.command()
    async def question(self, ctx: commands.Context, question_number: int) -> None:
        """Gets a question from the question bank depending on the question number provided."""
        question = self.questions.next_question(question_number)
        if isinstance(question, Embed):
            await ctx.send(embed=question)
            return

        (question_embed, time_limit), question_view = self.questions.current_question()
        await ctx.send(embed=question_embed, view=question_view)

        for time_remaining in range(time_limit - 1, -1, -1):
            await asyncio.sleep(1)
            if time_remaining % 5 == 0:
                await ctx.send(f"{time_remaining}s remaining")

        await ctx.send(embed=self.questions.end_question())

    @trivianight.command()
    async def list(self, ctx: commands.Context) -> None:
        """Displays all the questions from the question bank."""
        question_list = self.questions.list_questions()
        if isinstance(question_list, Embed):
            await ctx.send(embed=question_list)

        await ctx.send(question_list)

    @trivianight.command()
    async def stop(self, ctx: commands.Context) -> None:
        """End the ongoing question to show the correct question."""
        await ctx.send(embed=self.questions.end_question())

    @trivianight.command()
    async def end(self, ctx: commands.Context) -> None:
        """Ends the trivia night event and displays the scoreboard."""
        scoreboard_embed, scoreboard_view = await self.scoreboard.display()
        await ctx.send(embed=scoreboard_embed, view=scoreboard_view)


def setup(bot: Bot) -> None:
    """Load the TriviaNight cog."""
    bot.add_cog(TriviaNight(bot))
