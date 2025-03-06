from app.mc import builtin
from app.mc.markov_chain import MarkovChain
from app.mc.phrase_generator import PhraseGenerator

__version__ = "4.0.0"

# Expose MarkovChain class and PhraseGenerator for easy imports
mc = MarkovChain
# Make PhraseGenerator directly accessible via mc.PhraseGenerator
mc.PhraseGenerator = PhraseGenerator
