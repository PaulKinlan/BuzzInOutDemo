from google.appengine.ext import db

import random
import string

class BaseModel(db.Model):
  added_on = db.DateTimeProperty(auto_now_add = True)
  updated_on = db.DateTimeProperty(auto_now = True)

class User(BaseModel):
  profile = db.StringProperty() # The users google profile.
  uid = db.StringProperty() # The users google id for this service, it is not their true user_id
  oauth_token = db.StringProperty()
  oauth_token_secret = db.StringProperty()
  
  @staticmethod
  def Get(profile):
    return db.Query(User).filter("profile =", profile).get()
  
class Service(BaseModel):
  name = db.StringProperty()

class UserServices(BaseModel):
  user = db.ReferenceProperty(User)
  service = db.ReferenceProperty(Service)
  oauth_token = db.StringProperty()
  oauth_token_secret = db.StringProperty()
  
class Session(BaseModel):
  auth_token = db.StringProperty()
  session_id = db.StringProperty()
  user = db.ReferenceProperty(User)
  profile = db.StringProperty()
  buzzUrl = db.StringProperty()
  email = db.StringProperty()
  
  @staticmethod
  def MakeId():
    return ''.join([random.choice(string.letters) for i in xrange(64)])
  
  @staticmethod
  def GetSession(session_id, auth_token):
    return db.Query(Session).filter("auth_token =", auth_token).filter("session_id", session_id).get()