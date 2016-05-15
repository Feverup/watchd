
def recv( sock , buffsize=1024 ) :
    data = sock.recv(buffsize)
    size = int(data.split('\n')[0].split()[0]) + 1
    if size == 0 :
        print "ERROR : %s" % " ".join(data.split()[1:])
        return
    if size+1 == len(data.split('\n')) :
        return data.split('\n')[1]
    while size > 0 :
        buff = sock.recv(buffsize)
        data += buff
        items = buff.split('\n')
        size -= len(buff.split('\n'))
    return data.split('\n')[1:-1]

