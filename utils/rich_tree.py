from rich.console import Console
from rich.tree import Tree


def rich_tree_to_str(tree: Tree) -> str:
	console = Console()
	with console.capture() as capture:
		console.print(tree)
	return capture.get()