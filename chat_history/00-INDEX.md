# Made by [Claude](https://github.com/anthropics/claude-code)

First, all I did was:
- Load the initial implementation in a submodule (in case we may want to update the test suite...) so that he had access to both the initial implementation and the tests.
- Let him generate the initial `CLAUDE.md` file, he understood very well the structure of this repository and described it in quite a straightforward way.
- Added a few short sentences about what I wanted us to do.
- Asked `> I updated the CLAUDE.md file. What should we do now?`
- After that, I only said yes to everything. Some tests still didn't pass, but those were edge cases. He did follow my recommendations, and I thought he built the perfect adapter to run the tests in the original submodule with the new `pass.py` he also just built
- Actually, I just checked, those tests executed with the existing bash implementation... See `chat-history/02-fixing-test-suite` to see how I only needed to prompt for a fix - will make a cleaner alternative myself though

You can check the `chat-history` to follow the rest of our changes, I try to only give overall directions and not micromanage: it's funny seeing Claude making little mistakes, and fixing them just as fast as he made those...  
Feels like watching a beginner, but 10x, or even 100x faster... Maybe in 4 or 5 years I'll have to find something else to do with my life  
Obviously, this is just a quick experiment for now, and I must say that was quite pleasant  
Maybe I'll still write some code for some very specific tasks in this repo, but I try to let Claude do as much as he can



========
