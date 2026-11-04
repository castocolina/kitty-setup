from vulture.whitelist_utils import Whitelist

_ = Whitelist()

# Framework idioms a static checker cannot see through (R0.11, Phase 2 criterion 7)
_.completer  # argcomplete reads Action.completer at runtime
_.exc_type  # mandatory parameter of __exit__ (KittySession)
_.tb  # mandatory parameter of __exit__ (KittySession)
_.pytest_collection_modifyitems  # pytest hook called by name
_.BASH  # CompletionShell.BASH reached by value (installer.py:328, :340) and by iteration (:350, :365)
