import os
import datetime

from serveus.models import *


if os.path.isfile('cs198pythontest.db'):
	os.remove('cs198pythontest.db')

db.create_all()


# DEFAULT VALUES

# Malaria types
malaria_types = ['Falciparum', 'Vivax', 'Ovale', 'Malariae']
for i in malaria_types:
	for j in xrange(1,5):
		db.session.add(MalType(i, j))

# User types
user_types = ['Administrator', 'Doctor', 'Microscopist']
for user_type in user_types:
	db.session.add(UserType(user_type))

# DUMMY DATA

# Users
db.session.add(User('Rodolfo','genius123'))
db.session.add(User('Noel','qwert'))
db.session.add(User('Juancho','12345'))
db.session.add(User('Doctor Carl','lol'))

# Cases
db.session.add(Case(datetime.date(2005,8,26),20,'NCR (National Capital Region) Manila City','Vivax',14.58,121))
db.session.add(Case(datetime.date(2010,5,15),18,'CAR (Cordillera Administrative Region) Baguio City','Falciparum',16.42,120.6))
db.session.add(Case(datetime.date(2007,1,5),24,'NCR (National Capital Region) Quezon City','Ovale',14.67,121))

# TODO: remove when keys are synced with accounts
"""
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES

private_key = RSA.generate(1024)
public_key = private_key.publickey()
private_key = private_key.exportKey()
public_key = public_key.exportKey().replace('-----BEGIN PUBLIC KEY-----','').replace('-----END PUBLIC KEY-----','').replace('\n','')
db.session.add(Key(private_key, public_key))
"""
public_key = """MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCbMiQNyj/Nzj7QQBj8nAx3WKPy4r72Onnw/E9KQY1gUwepRtCKYgJz9typvvfi7zNROFp5o8OBL5mVWFShxMIh57entYRpZUGtTZtb7YT5Bx3ZM5FPKQzHcJDyPJFloJW6V0+jmmZSosvM4nrZknVW3DABdmiVadGXtdy9DNevyQIDAQAB"""
private_key = """-----BEGIN RSA PRIVATE KEY-----\nMIICXQIBAAKBgQCbMiQNyj/Nzj7QQBj8nAx3WKPy4r72Onnw/E9KQY1gUwepRtCK\nYgJz9typvvfi7zNROFp5o8OBL5mVWFShxMIh57entYRpZUGtTZtb7YT5Bx3ZM5FP\nKQzHcJDyPJFloJW6V0+jmmZSosvM4nrZknVW3DABdmiVadGXtdy9DNevyQIDAQAB\nAoGAF7J9TNnAClXew3+2EQRm5uZTCmhTDlf5fLGaDdWal8W12sQkXaz/gOOF6Clv\nwmgR5un67q3x0U0KX4KAUb8wgS2wlkWYlT062+mE7cYKZh07ZxCFy+yrfM6qRrvA\nHJPa60TTAQTRXSeoX9DrWHld+JVKml74vV3oQSThdgj70d0CQQC1Ei48dhfmCurY\nsVPjHR6Sx0URqtHvZMHJrW1eMa0X0QHSs9iSXFZmQGD5qprQBjNmMrQe8zd4Uwto\ntPMnPSxjAkEA22rd7deGlaWaaTosMF12ikzMd1KP42IK+BWMIh6HfoXcxj7H1pQ7\nS7oSNgqqIojgGLZfIc9bKfa0sSp6GE+c4wJBAKd2vRRmFAxKJJFsz6zJDbGqYpLI\nbYj+osunffMT9oaEYy8/7hjPFYlUGVxPEQc79OWcF0JYpwC9rVuVnxy3UwkCQQCw\nnCk8OyGyLFTIZDGTUHeMxFpDpSn6PT1VCIr+H5KyLW9SBtB1kGTWBFSKOTVOjNvM\nKGcUYMIhWdmBTQ5vqQ0/AkAx2XcV90V/6i89F2SElT3OcQsjznPJ58TupP5Ckr6l\n3i8SY+/pip4zPV0/gdS21VbaOEvwxaVOUcm1anNmBmRs\n-----END RSA PRIVATE KEY-----"""
db.session.add(Key(private_key, public_key))

# COMMIT
db.session.commit()