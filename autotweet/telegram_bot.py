""":mod:`autotweet.command` --- CLI interface
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module provides abillities to connect to telegram.

"""
from __future__ import unicode_literals

from telegram.ext import CommandHandler, Updater, MessageHandler, Filters, BaseFilter

from .learning import DataCollection, NoAnswerError
from .logger_factory import get_logger


class ReplyFilter(BaseFilter):
    def filter(self, message):
        return bool(message.reply_to_message)

Filters.reply = ReplyFilter()

logger = get_logger(__name__)




class TelegramBot(object):
    def __init__(self, db_uri, token, threshold, learning=True, answering=True):
        self._make_updater(token)

        self.threshold = threshold
        self.data_collection = DataCollection(db_uri)

        self._init_handlers()
        if learning:
            self.enable_learning()
        if answering:
            self.enable_answering()

    def run(self):
        logger.info('Starting with {} documents.'.format(self.data_collection.get_count()))
        self.updater.start_polling()
        self.updater.idle()

    def learning_handler(self, bot, update):
        question = update.message.reply_to_message.text
        answer = update.message.text
        self.data_collection.add_document(question, answer)

    def answering_handler(self, bot, update):
        question = update.message.text
        try:
            answer, ratio = self.data_collection.get_best_answer(question)
            if ratio > self.threshold:
                logger.info('{} -> {}'.format(question, answer))
                update.message.reply_text(answer, reply_to_message_id=update.message.message_id)
        except NoAnswerError:
            logger.debug('No answer to {}'.format(question))

    def leave_handler(self, bot, update):
        logger.info('Leave from chat {}'.format(update.message.chat_id))
        bot.leave_chat(update.message.chat_id)

    def enable_learning(self):
        logger.debug('Enabling learning handler.')
        self.dispatcher.add_handler(MessageHandler(Filters.reply, self.learning_handler))

    def enable_answering(self):
        logger.debug('Enabling answer handler.')
        self.dispatcher.add_handler(MessageHandler(Filters.text, self.answering_handler))

    def _make_updater(self, token):
        self.updater = Updater(token)
        self.dispatcher = self.updater.dispatcher

    def _init_handlers(self):
        self.dispatcher.add_handler(CommandHandler('leave', self.leave_handler))


def start_bot(token, db_uri, threshold, learning=True, answering=True):
    bot = TelegramBot(db_uri, token, threshold, learning, answering)
    bot.run()
