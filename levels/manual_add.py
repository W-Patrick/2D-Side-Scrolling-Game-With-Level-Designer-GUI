import json
import sys

print "----------------------------------------"
print "             MANUAL ADD                 "
print "----------------------------------------"


platforms = {
    "platforms": []
}

name = raw_input("File name: ")
print "\n"


def export(name):
    with open(name + ".json", "w") as filename:
        json.dump(platforms, filename, indent=4)

    print name + " was exported."
    sys.exit()


while True:

    ptype = raw_input("Type: ")
    x = raw_input("x: ")
    y = raw_input("y: ")

    platforms["platforms"].append({
        "y": int(y),
        "x": int(x),
        "type": ptype
    })

    proper_response = False
    while not proper_response:
        print "Done? (Y/N)"
        answer = raw_input("> ")
        responses = ["y", "Y", "n", "N"]
        if answer in responses:
            if answer.lower() == "y":
                export(name)
            else:
                proper_response = True
                pass
        else:
            print "Not a proper response\n"
