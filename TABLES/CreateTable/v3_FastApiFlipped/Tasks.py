
def checkSess(usDoc, device, roomLink):
    if usDoc['Session']['device'] != device:
        return 1, "user logged with other device"
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
    print("checkSess skipped")
    return 0, None