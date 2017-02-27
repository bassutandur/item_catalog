from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Base, Category, Item, User

engine = create_engine('sqlite:///catalogitems.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()


# Create dummy user
User1 = User(name="Basavaraj Tandur", email="bassu.tandur@gmail.com",
             picture='imageurl')
session.add(User1)
session.commit()

# Add Categories
category1 = Category(name="Soccer")
session.add(category1)
session.commit()

item1 = Item(user_id=1,
             name="Footwear",
             description=("These shoes provide better traction on grass,"
                          "which increases player's ability to stay"
                          "on their feet"),
             category=category1)

session.add(item1)
session.commit()

item1 = Item(user_id=1,
             name="Shin Guards",
             description=("Shin-guards protect player's shins,"
                          "a vulnerable part of a player's body"
                          "that often gets kicked"),
             category=category1)

session.add(item1)
session.commit()

item1 = Item(user_id=1,
             name="Soccer Ball",
             description=("Soccer balls allows players to"
                          "play individually or with friends"
                          "outside of practice"),
             category=category1)

session.add(item1)
session.commit()


category2 = Category(name="Basketball")
session.add(category2)
session.commit()

category3 = Category(name="Baseball")
session.add(category3)
session.commit()

category4 = Category(name="Frisbee")
session.add(category4)
session.commit()

category5 = Category(name="Snowboarding")
session.add(category5)
session.commit()

category6 = Category(name="Rock climbing")
session.add(category6)
session.commit()

category7 = Category(name="Foosball")
session.add(category7)
session.commit()

category8 = Category(name="Skating")
session.add(category8)
session.commit()

category9 = Category(name="Hockey")
session.add(category9)
session.commit()

category10 = Category(name="Cricket")
session.add(category10)
session.commit()

item1 = Item(user_id=1,
             name="Cricket Ball",
             description=("Cricket balls allows players to"
                          "train and play individually or with friends"),
             category=category10)

session.add(item1)
session.commit()

item1 = Item(user_id=1,
             name="Inner Gloves",
             description="Cotton padded & unpadded glove",
             category=category10)

session.add(item1)
session.commit()

item1 = Item(user_id=1,
             name="Cricket Stumps",
             description=("Wooden normal stumps"
                          "natural wax finish with 2 half"
                          "bails or 1 single full bail"),
             category=category10)

session.add(item1)
session.commit()

item1 = Item(user_id=1,
             name="Cricket Bat",
             description=("Cricket bats available"
                          "in various size & finish"),
             category=category10)

session.add(item1)
session.commit()


print "added Catalog items!"
