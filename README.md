<a href="https://www.buymeacoffee.com/michaeltherat"><img src="https://img.buymeacoffee.com/button-api/?text=Buy me a rat&emoji=🐀&slug=michaeltherat&button_colour=FFDD00&font_colour=000000&font_family=Comic&outline_colour=000000&coffee_colour=ffffff"></a>
# Rajce Downloader and Analyzer
Command-line program to download photos and videos from rajce.idnes.cz. 
```
rajce.py [OPTIONS] -u URL [URL ...]
```
## Options
    -h, --help                                        Show this help message and exit
    -u, --url URL [URL ...]                           URLs to download or to analyze
    -p, --path PATH                                   Destination folder
    -b, --bruteforce                                  Use bruteforce            
    -H, --history                                     Download only videos not listed in the
                                                      history file. Record the IDs of all
                                                      downloaded photos and videos in it
    -a, --analyze [ALBUM_TOP_SIZE, [MEDIA_TOP_SIZE]]  Analyze URLs and show (by default) top10
                                                      albums and Top50 photos based on rating. 
                                                      You can change Tops' sizes.    
    
## How to use
    
#### Allowed formats for `--url` option. 
```
userName
https://userName.rajce.idnes.cz
https://userName.rajce.idnes.cz/albumName
"https://username.rajce.idnes.cz/albumName/?login=login&code=password"
```
You can use multiple urls and userNames. Quotes are required when URL has album credentials.

#### Using `--analyze` flag.  
By default, `ALBUM_TOP_SIZE` = 10 and `MEDIA_TOP_SIZE` = 50.  
So, `-a` without any extra parameters is the same as `-a 10 50`.  
Few examples:  
Show albums Top3 and photos Top10 - `-a 3 10`.  
Show only photos Top13 - `-a 0 13`  
```
NOTE! When you use --analyze flag script will not download files
```

#### Bruteforce flag `-b`
Trying to access password protected albums with all combinations of userName and albumName as credentials. 
Don't overuse this flag, you can be banned. 
Better apply this flag for single album test.

## Requirements
* [Python 3.6](https://www.python.org/downloads)
