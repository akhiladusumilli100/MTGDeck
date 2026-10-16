CARD_DATABASE_ALIAS = 'cards_db'


CARD_DATABASE_APPS = {'cards', 'decks'}


class CardsDatabaseRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label in CARD_DATABASE_APPS:
            return CARD_DATABASE_ALIAS

    def db_for_write(self, model, **hints):
        if model._meta.app_label in CARD_DATABASE_APPS:
            return CARD_DATABASE_ALIAS

    def allow_relation(self, obj1, obj2, **hints):
        if {obj1._meta.app_label, obj2._meta.app_label} <= CARD_DATABASE_APPS:
            return True

    def allow_migrate(self, db, app_label, **hints):
        if app_label in CARD_DATABASE_APPS:
            return db == CARD_DATABASE_ALIAS
        return db == 'default'