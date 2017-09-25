import collections
import datetime
import itertools
import logging
import random
import re
import sqlite3
import threading
import asyncio

import discord

from komida_parser import KomidaUpdate


def get_campus(text):
    """
    Check which campus is mentioned in the given text.

    A campus can be denoted by its full name or by its three-letter acronym.

    Args:
        text: The text in which the occurrence of the campuses is checked.

    Returns:
        A list with acronyms for all UAntwerp campuses that were mentioned in the text. Defaults to CMI if no campus is
        explicitly mentioned.
    """
    campus_options = [('cde', ['cde', 'drie eiken']),('cmi', ['cmi', 'middelheim']), ('cst', ['cst', 'stad', 'city'])]

    campus = sorted([c_code for c_code, c_texts in campus_options if any(c_text in text for c_text in c_texts)])
    return campus if len(campus) > 0 else ['cmi']


def get_date(text):
    """
    Check which date is mentioned in the given text.

    A date can be referred to by the day of week (Monday - Sunday) or by 'yesterday', 'today', and 'tomorrow'.

    Args:
        text: The text in which the occurrence of dates is checked.

    Returns:
        A list with `datetime` objects for all of the dates that were mentioned in the text. Defaults to today if no
        date is explicitly mentioned.
    """
    today = datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    date_options = [('today', 0), ('tomorrow', 1), ('yesterday', -1), ('monday', 0 - today.weekday()),
                    ('tuesday', 1 - today.weekday()), ('wednesday', 2 - today.weekday()),
                    ('thursday', 3 - today.weekday()), ('friday', 4 - today.weekday()),
                    ('saturday', 5 - today.weekday()), ('sunday', 6 - today.weekday())]

    dates = sorted([today + datetime.timedelta(days=date_diff) for day, date_diff in date_options if day in text])
    return dates if len(dates) > 0 else [today]


def get_menu(campuses, dates):
    """
    Retrieve the menu on the given dates for the given campuses from the database.

    Args:
        campuses: The campuses for which the menu is retrieved.
        dates: The dates for which the menu is retrieved.

    Returns:
        A nested dictionary with as keys the requested dates and campuses, and for each of these possibilities a
        dictionary with as key the type of menu item and as values the menu content and the prices for students and
        staff.
    """
    conn = sqlite3.connect('menu.db')
    c = conn.cursor()

    menu = collections.defaultdict(dict)
    for date, campus in itertools.product(dates, campuses):
        c.execute('SELECT type, item, price_student, price_staff FROM menu WHERE date = ? AND campus = ?', (date, campus))
        for menu_type, menu_item, price_student, price_staff in c.fetchall():
            menu[(date, campus)][menu_type] = (menu_item, price_student, price_staff)

    return menu


def create_attachments(menu):
    """
    Format the given menu as a Slack attachment.

    Args:
        menu: A nested dictionary with as keys the dates and campuses and as values a menu items dictionary.

    Returns:
        A list of individual menus as a dictionary formatted to be used as a Slack attachment.
    """
    campus_colors = {'cde': 'good', 'cgb': 'warning', 'cmi': 'danger', 'cst': '#439FE0'}

    attachments = []
    for (date, campus), menu_items in menu.items():
        attachments.append({'title': 'Menu komida {} on {}'.format(campus.upper(), date.strftime('%A %d %B')),
                            'color': campus_colors[campus], 'text': format_menu(menu_items)})

    return attachments


def format_menu(menu):
    """
    Textually format a menu.

    Args:
        menu: A dictionary with as key the type of menu item and as values the menu content and the prices for students
              and staff.

    Returns:
        The nicely format menu including emojis to indicate the menu types.
    """
    message = []
    if 'soup' in menu:
        message.append(':tea: {} (€{:.2f} / €{:.2f})'.format(*menu['soup']))
    if 'vegetarian' in menu:
        message.append(':tomato: {} (€{:.2f} / €{:.2f})'.format(*menu['vegetarian']))
    if 'meat' in menu:
        message.append(':poultry_leg: {} (€{:.2f} / €{:.2f})'.format(*menu['meat']))
    for key in menu.keys():
        if 'grill' in key:
            message.append(':meat_on_bone: {} (€{:.2f} / €{:.2f})'.format(*menu[key]))
    for key in menu.keys():
        if 'pasta' in key:
            message.append(':spaghetti: {} (€{:.2f} / €{:.2f})'.format(*menu[key]))

    return '\n'.join(message)

'''
class KomidaBot(discord.Client):
    def __init__(self):
        self.update = None
        super(KomidaBot, self).__init__()

    @asyncio.coroutine
    def on_ready(self):
        self.update = KomidaUpdate()
        self.updateMenu()

    def updateMenu(self):
        self.update.run()
        t= threading.Timer(7200,self.updateMenu)


    @asyncio.coroutine
    def on_message(self,message):
        print('Here')
        if (message.author == self.user):
            return
        print('Here')
        if (self.user not in message.mentions):
            return
        print('Here')
        await self.send_message(message.channel, 'I was mentioned?')

        text = temp.content.lower()
            
        campuses = get_campus(text)
        dates = get_date(text)

        # get the requested menus
        menus = get_menu(campuses, dates)
        # force a menu update if nothing could be found initially
        if len(menus) == 0:
            try:
                logging.debug('No menu found, updating...')

                this.send_message(message.channel, "I don't have the menu for {} on {}. Let me see if I can find it online...".format(', '.join(campuses).upper(), ', '.join([d.strftime('%A %d %B') for d in dates]))

                # force a menu update and try to retrieve the requested menu again
                self.update.run()
                menus = get_menu(campuses, dates)
            except Exception as e:
                logging.exception('Problem while updating the menu: {}'.format(e))

        # reply with the menu
        if len(menus) > 0:
            response = self.send_message(message.channel, 'bla')
        # or send a final message that no menu could be found
        else:
            fail_gifs = ['https://giphy.com/gifs/monkey-laptop-baboon-xTiTnJ3BooiDs8dL7W',
                         'https://giphy.com/gifs/office-space-jBBRs81dGWHIY',
                         'https://giphy.com/gifs/computer-Zw133sEVc0WXK',
                         'https://giphy.com/gifs/computer-D8kdCAJIoSQ6I',
                         'https://giphy.com/gifs/richard-ayoade-it-crowd-maurice-moss-dbtDDSvWErdf2']
            response = self.send_message(message.channel,"_COMPUTER SAYS NO._ I'm sorry, no menu has been found.\n{}".format(random.choice(fail_gifs)))
        

    def process_message(self, data):
        """
        Check if the received Slack message is a menu request and answer if needed.

        A menu can be requested on public channels to which the komidabot is invited by:
        - Mentioning 'komidabot', optionally including a date and campus specification.
        - Matching the '^l+u+n+c+h+!+$' regex to retrieve the default menu (today at campus Middelheim).
        Or by messaging the komidabot directly.

        A Slack response with the menu or a notification that the requested menu could not be found is sent.

        Args:
            data: The Slack message.
        """
        # ignore messages by the bot itself or from other bots
        if data.get('username') == 'komidabot' or 'bot' in data.get('subtype', []):
            return
        # ignore messages that don't contain the text as we expect it to
        if 'text' not in data:
            return
        else:
            text = data['text'].lower()
        # ignore messages on public channels that don't contain the trigger word (lunch)
        if data.get('channel').startswith('C') and not\
                ('komidabot' in text or re.search('^l+u+n+c+h+!+$', text) is not None):
            return

        # parse the campus(es) and date(s) from the request
        campuses = get_campus(text)
        dates = get_date(text)

        # get the requested menus
        menus = get_menu(campuses, dates)
        # force a menu update if nothing could be found initially
        if len(menus) == 0:
            try:
                logging.debug('No menu found, updating...')

                response = self.slack_client.api_call('chat.postMessage', channel=data['channel'],
                                                      text="I don't have the menu for {} on {}. Let me see if I can find it online...".format(
                                                          ', '.join(campuses).upper(), ', '.join([d.strftime('%A %d %B') for d in dates])),
                                                      username='komidabot', icon_emoji=':fork_and_knife:')
                if not response['ok']:
                    self.process_error(data['channel'], response['error'])

                # force a menu update and try to retrieve the requested menu again
                self.update.run(self.slack_client)
                menus = get_menu(campuses, dates)
            except Exception as e:
                logging.exception('Problem while updating the menu: {}'.format(e))

        # reply with the menu
        if len(menus) > 0:
            response = self.slack_client.api_call('chat.postMessage', channel=data['channel'], text='*LUNCH!*',
                                                  attachments=create_attachments(menus),
                                                  username='komidabot', icon_emoji=':fork_and_knife:')
        # or send a final message that no menu could be found
        else:
            fail_gifs = ['https://giphy.com/gifs/monkey-laptop-baboon-xTiTnJ3BooiDs8dL7W',
                         'https://giphy.com/gifs/office-space-jBBRs81dGWHIY',
                         'https://giphy.com/gifs/computer-Zw133sEVc0WXK',
                         'https://giphy.com/gifs/computer-D8kdCAJIoSQ6I',
                         'https://giphy.com/gifs/richard-ayoade-it-crowd-maurice-moss-dbtDDSvWErdf2']
            response = self.slack_client.api_call('chat.postMessage', channel=data['channel'],
                                                  text="_COMPUTER SAYS NO._ I'm sorry, no menu has been found.\n{}".format(random.choice(fail_gifs)),
                                                  username='komidabot', icon_emoji=':fork_and_knife:')

        # check if the menu was correctly sent
        if not response['ok']:
            self.process_error(data['channel'], response['error'])

    def process_error(self, channel, reason):
        """
        Send a Slack message to notify the user of an occurred error.

        If the notification cannot be sent an error is logged.

        Args:
            channel: To channel to which to send the notification.
            reason: The error reason.
        """
        # log the error
        logging.error('Failed to post to Slack: {}'.format(reason))

        # try to send an error message upon a failure
        response = self.slack_client.api_call('chat.postMessage', channel=channel,
                                              text="I'm sorry, I can't tell you the menu. Error status: {}".format(reason),
                                              username='komidabot', icon_emoji=':fork_and_knife:')

        # check the error status of this message but don't try to resend
        if not response['ok']:
            logging.error('Failed to post to Slack: {}'.format(response['error']))
'''

def run():
    client = discord.Client()
    parser = KomidaUpdate()

    def updateMenu():
        parser.run()
        t = threading.Timer(7200, updateMenu)

    @client.event
    async def on_ready():
        updateMenu()


    @client.event
    async def on_message(message):

        if message.author == client.user:
            return
        if client.user not in message.mentions:
            return

        text = message.content

        campuses = get_campus(text)
        dates = get_date(text)

        # get the requested menus
        menus = get_menu(campuses, dates)

        # force a menu update if nothing could be found initially
        if len(menus) == 0:
            await client.send_message(message.channel, "I don't have the menu for {} on {}. Let me see if I can find it online...".format(', '.join(campuses).upper(), ', '.join([d.strftime('%A %d %B') for d in dates])))

            # force a menu update and try to retrieve the requested menu again
            parser.run() 
            menus = get_menu(campuses, dates)

        # reply with the menu
        if len(menus) > 0:
            # STILL FIND THE MENU
            attachments = create_attachments(menus)
            for att in attachments:
                await client.send_message(message.channel,att['title']+'\n'+att['text'])
        # or send a final message that no menu could be found
        else:
            fail_gifs = ['https://giphy.com/gifs/monkey-laptop-baboon-xTiTnJ3BooiDs8dL7W',
                         'https://giphy.com/gifs/office-space-jBBRs81dGWHIY',
                         'https://giphy.com/gifs/computer-Zw133sEVc0WXK',
                         'https://giphy.com/gifs/computer-D8kdCAJIoSQ6I',
                         'https://giphy.com/gifs/richard-ayoade-it-crowd-maurice-moss-dbtDDSvWErdf2']
            await client.send_message(message.channel,"_COMPUTER SAYS NO._ I'm sorry, no menu has been found.\n{}".format(random.choice(fail_gifs)))


    client.run('MzU4NjY1MTkwMjM1MDQ1ODg4.DKfxsQ.K6fhXxQ9EwAo8sFkplooHln2s0o')


if __name__ == '__main__':
    run()
    