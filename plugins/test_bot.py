import asyncio
import discord
import sched
import threading

client = discord.Client()

def foo():
    print('bla')
    t = threading.Timer(5.0,foo)
    t.start()

t = threading.Timer(10.0,foo)
t.start()




@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

@client.event
async def on_message(message):
    if message.content.startswith('!test'):
        counter = 0
        tmp = await client.send_message(message.channel, 'Calculating messages...')
        async for log in client.logs_from(message.channel, limit=100):
            if log.author == message.author:
                counter += 1

        await client.edit_message(tmp, 'You have {} messages.'.format(counter))
    elif message.content.startswith('!sleep'):
        await asyncio.sleep(5)
        await client.send_message(message.channel, 'Done sleeping')


client.run('MzU4NzE3Mjc1NDUwMjQ1MTIx.DJ8hEQ.y01HKYsI8OdhzgtKBFeODNvrcvk')
