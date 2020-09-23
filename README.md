# pythonFabricDemo
Demonstration of some fabric commands in a handy object

Intended for use by a few colleagues as a starter example. The idea is that you READ THE CODE before running stuff to make sure it is doing what you expect.


```
demo.py --help
```

To get a default config file do

```
demo.py --template demo > conf.json
```

and then edit for your values

Start off with configuring your jump host and your target host and then use

```
demo.py confirm
```

to check if they work

then you can do something like

```
demo.py tunnel
```

and login to your remote target and see if you can telnet to the configured port

```
telnet localhost 22022
```

finally try the full demo, this should connect you to github through the tunnel and clone another one of my public repos.

```
demo.py demo
```
