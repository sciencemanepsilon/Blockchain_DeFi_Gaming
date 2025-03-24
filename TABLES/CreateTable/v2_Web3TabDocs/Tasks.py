
def checkSess(usDoc, device, roomLink):
    print("DB device: "+ usDoc['Session']['device'])
    if usDoc['Session']['device'] != device:
        return 1, "user logged with other device"
    print("DB Sess.status: "+ usDoc['Session']['status'])
    if "-" in usDoc['Session']['status']:
        tInfo = usDoc['Session']['status'].split("-")
        return 2, {
            'error':'User inGame',
            'link':roomLink +tInfo[2] +"&gameCollection=" +tInfo[1]
        }    
    if "?" in usDoc['Session']['status']:
        return 3, {
            'error':'user in Que',
            'msg':'Please exit the Quickmatch-Que to create a table'
        }
    print("Sessio checks passed")
    return 0, None