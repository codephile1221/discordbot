import asyncio
from constants import RADIOS
import discord
from discord.ext import commands

import youtube_dl
from youtube_search import YoutubeSearch


def active_voice(ctx):
    bot_voice = ctx.guild.voice_client
    if bot_voice is None:
        return False
    author_voice = ctx.message.author.voice
    if (author_voice is not None and bot_voice.channel == author_voice.channel
            and not author_voice.self_deaf and not author_voice.deaf):
        return True

    return ctx.author == ctx.guild.owner


class Song:
    def __init__(self, url, stream_url, title, duration, thumbnail, requestor):
        self.url = url
        self.stream_url = stream_url
        self.title = title
        self.duration = duration
        self.thumbnail = thumbnail
        self.requestor = requestor


# TODO: Custom help command
class Music(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.voice_states = dict()
        self.playlists = dict()
        self.currentsongs = dict()
        self.repeatsong = False

    @commands.command()
    async def poem(self, ctx):  # TODO: add poems
        await ctx.channel.send('''*clears throat*
        My daddy cry if I fail ...
        then I hit you and go to jail ...
        but don't worry I get easy bail ...
        then I again hit you, again jail, again bail ...
        then jail bail, jail bail, jail bail ...
        and one day your heart fail''')

    @commands.command(aliases=['j', 'aaja'])
    async def join(self, ctx):

        author_voice = ctx.message.author.voice
        voice_state = self.voice_states.get(ctx.guild, None)

        if not voice_state:
            if author_voice:
                await ctx.message.author.voice.channel.connect()
                await ctx.channel.send(
                    '**Meh raazi! Tu raazi! `Connected to your VC`**')
                voice_state = ctx.message.guild.voice_client
                self.voice_states[ctx.guild.id] = voice_state
                self.playlists[ctx.guild.id] = []
            else:
                await ctx.channel.send(
                                "**Meh raazi, lekin Tu nahi raazi. "
                                " `Please connect to a VC first.`**")
        else:
            await ctx.channel.send(
                '**Arree BC, I\'m already connected to a VC**'
                                )

    def playsong(self, ctx):
        '''Master play function'''

        playlist = self.playlists[ctx.guild.id]
        if self.repeatsong:
            self.repeatsong = False
        elif len(playlist) > 0:
            self.currentsongs[ctx.guild.id] = playlist.pop(0)
        else:
            return  # no songs in queue and repeat is off

        voice_state = self.voice_states.get(ctx.guild.id, None)
        before_options = (
            "-reconnect 1 "
            "-reconnect_streamed 1 "
            "-reconnect_delay_max 5")
        voice_state.play(
            discord.FFmpegPCMAudio(
                self.currentsongs[ctx.guild.id].stream_url,
                before_options=before_options),
            after=lambda e: self.playsong(ctx)
                        )
        asyncio.run_coroutine_threadsafe(ctx.channel.send(
            "\U0001f4c0`Aapko Sunaana Chaahta Hoon:`"
            f"\U0001f4c0\n{self.currentsongs[ctx.guild.id].url}"),
                self.bot.loop)

    @commands.command()
    @commands.check(active_voice)
    async def radio(self, ctx, radio):
        '''
        stream urls of radio stations in .env file
        '''
        radio = radio.upper()
        if radio not in RADIOS.keys():
            await ctx.send(
                "radio station not found.\n"
                f"Available radio stations are {', '.join(RADIOS.keys())}.")
            return

        radio_ = Song(
                url=f"{radio} radio",
                stream_url=RADIOS[radio],
                title=radio,
                duration="LIVE radio",
                thumbnail=None,
                requestor=ctx.author)
        playlist = self.playlists[ctx.guild.id]
        playlist.insert(0, radio_)

        voice_state = self.voice_states[ctx.guild.id]
        if voice_state.is_playing():
            self.repeatsong = False
            voice_state.stop()
        else:
            self.playsong(ctx)

    @commands.command()
    @commands.check(active_voice)
    async def play(self, ctx, *args):
        if len(args) == 0:
            await self.resume_(ctx)
            return

        searchquery = ' '.join(args)

        YTresults = YoutubeSearch(searchquery, max_results=1).to_dict()
        for result in YTresults:
            url_ = 'https://www.youtube.com' + result['url_suffix']
            title = result.get('title')
            duration = result.get('duration')
            thumbnail = result.get('thumbnails')[0]

        try:
            ydl_opts = {'quiet': True}
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(url_, download=False)
                stream_url = result['formats'][0]['url']
        except Exception as e:
            await ctx.channel.send(f'**`{type(e).__name__} : {e}`**\U0001f62c')

        voice_state = self.voice_states[ctx.guild.id]
        playlist = self.playlists[ctx.guild.id]
        if voice_state.is_playing():
            await ctx.channel.send(f'`{title}` has been added to queue')
            songObj = Song(
                url_, stream_url, title,
                duration, thumbnail, ctx.message.author)
            playlist.append(songObj)
            return
        else:
            songObj = Song(
                url_, stream_url, title,
                duration, thumbnail, ctx.message.author)
            playlist.append(songObj)
            self.playsong(ctx)

    @commands.command(name='pause', aliases=['rokku'])
    @commands.check(active_voice)
    async def pause_(self, ctx):
        '''Pauses the current playing song'''
        voice_state = self.voice_states.get(ctx.guild.id, None)
        if voice_state:
            voice_state.pause()
            await ctx.channel.send(
                "*Me karu intezer tera...*"
                "`Song has been paused` \u23f8")

    @commands.command(name='resume')
    @commands.check(active_voice)
    async def resume_(self, ctx):
        '''Resumes the paused song'''
        voice_state = self.voice_states.get(ctx.guild.id, None)
        if voice_state and voice_state.is_paused():
            await ctx.channel.send("*RESUMING bhai...*\u23ef")
            voice_state.resume()

    @commands.command(aliases=['s', 'hutt'])
    @commands.check(active_voice)
    async def skip(self, ctx):  # TODO: vote
        voice_state = self.voice_states.get(ctx.guild.id, None)
        if voice_state:
            if voice_state.is_playing():
                await ctx.channel.send("**`song skipped`** \U0001fa93")
            else:
                await ctx.channel.send("No songs to skip\U0001f926")
            voice_state.stop()
            self.repeatsong = False

    @commands.command()
    @commands.check(active_voice)
    async def repeat(self, ctx):
        '''Repeats the current playing song ONCE'''
        voice_state = self.voice_states.get(ctx.guild.id, None)
        if voice_state:
            if not self.repeatsong:
                self.repeatsong = True
                await ctx.channel.send("**`Repeat: ON`** \U0001f502")
            else:
                self.repeatsong = False
                await ctx.channel.send("**`Repeat: Cancelled`**\U0001f645")

    @commands.command(aliases=['r'])
    @commands.check(active_voice)
    async def remove(self, ctx, position: int):
        '''Removes song at position from queue'''
        voice_state = self.voice_states.get(ctx.guild.id, None)
        playlist = self.playlists.get(ctx.guild.id, None)
        if voice_state and playlist:
            if position < 0:
                s = playlist.pop(position)
            else:
                s = playlist.pop(position-1)
            await ctx.channel.send(f"**removed `{s.title}` from the queue**")
            del s

    @commands.command(aliases=['m'])
    async def move(self, ctx, initial: int, final: int = 1):
        '''Moves song from the specified intial position to final position'''
        voice_state = self.voice_states.get(ctx.guild.id, None)
        playlist = self.playlists.get(ctx.guild.id, None)
        if voice_state and playlist:
            if initial < 1 or final < 1:
                await ctx.channel.send("`Invalid Arguments, naughty boy`")
                return
            s = playlist.pop(initial-1)
            playlist.insert(final-1, s)
            await ctx.channel.send(
                f"**`{s.title}` moved to "
                "position {final}** \u2705")
            del s

    @commands.command(name='clear')
    @commands.check(active_voice)
    async def clear_(self, ctx):
        voice_state = self.voice_states.get(ctx.guild.id, None)
        if voice_state:
            self.playlists[ctx.guild.id].clear()
            await ctx.channel.send("`Queue has been cleared`\u2705")

    @commands.command(name='queue', aliases=['q', 'gaanas'])
    async def listqueue(self, ctx):
        '''List the songs in queue'''

        voice_state = self.voice_states.get(ctx.guild.id, None)
        playlist = self.playlists.get(ctx.guild.id, None)
        if voice_state:
            if playlist:
                embed = discord.Embed(
                    title='Yeh hei tera queue:',
                    colour=discord.Colour.gold())
                embed.description = "Now Playing:"
                f"{self.currentsongs[ctx.guild.id].title}"
                for song in playlist:
                    embed.add_field(
                        name=song.title,
                        value=f"Requested by: {song.requestor}\n"
                        f"Duration: {song.duration}",
                        inline=False)

            else:
                embed = discord.Embed(
                    title='Abbe...',
                    description="Queue is empty",
                    colour=discord.Colour.red())

            await ctx.channel.send(embed=embed)

    @commands.command(aliases=['np'])
    async def nowplaying(self, ctx):  # TODO: Duration left
        voice_state = self.voice_states.get(ctx.guild.id, None)
        currentsong = self.currentsongs.get(ctx.guild.id, None)
        if voice_state:
            if voice_state.is_playing() or voice_state.is_paused():
                embed = discord.Embed(
                    title='Now playing:',
                    colour=discord.Colour.blurple())
                embed.add_field(
                    name=f'{currentsong.title}',
                    value=f"Requested by: {currentsong.requestor}"
                    f"\nDuration: {currentsong.duration}")
                if currentsong.thumbnail:
                    embed.set_thumbnail(url=currentsong.thumbnail)

            else:
                embed = discord.Embed(
                    title='Hmmm...',
                    description='Currently not playing a song',
                    colour=discord.Colour.red())

            await ctx.channel.send(embed=embed)

    @commands.command(help="Disconnects from Voice Channel", aliases=['dis'])
    @commands.check(active_voice)
    async def disconnect(self, ctx):
        voice_state = self.voice_states.get(ctx.guild.id, None)
        if voice_state:
            await voice_state.disconnect()
            await ctx.channel.send("`Disconnected from VC`")
            playlist = self.playlists.get(ctx.guild.id, None)
            if playlist:
                del playlist

    async def cog_command_error(self, ctx, error):

        if isinstance(error, commands.CheckFailure):
            bot_voice = ctx.message.guild.voice_client
            author_voice = ctx.message.author.voice

            if bot_voice is None or author_voice is None\
                    or bot_voice.channel != author_voice.channel:
                await ctx.channel.send(
                                    "**`Please connect to the same VC as "
                                    f"`{self.bot.user.mention}`to use this "
                                    "command`\U0001f926\u200d\u2642\ufe0f**"
                                        )
            elif author_voice.self_deaf:
                await ctx.channel.send(
                                    "**`Nuh uh, can't use this command "
                                    "while deafened.`**")

            elif author_voice.deaf:
                await ctx.channel.send(
                    f"{ctx.author.mention}**`Server deafen "
                    "go Brrrrrrrrrr...`**")


def setup(bot):
    bot.add_cog(Music(bot))
    print("Added music cog")
