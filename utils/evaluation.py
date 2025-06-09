from __future__ import annotations
from typing import Optional
import os
import difflib

def tree_edit_distance(pred: ParsedBlock, ground_truth: ParsedBlock) -> dict[str, float]:
	"""
	Zhang-Shasha algorithm
	"""
	import zss
	class ZSSNode(zss.Node):
		def __init__(self, label, children):
			super().__init__(label=label, children=children)

		@classmethod
		def from_block(cls, block: ParsedBlock) -> ZSSNode:
			return cls(
				label=block.text,
				children=[ZSSNode.from_block(block=child) for child in block.children] if block.children is not None else []
			)

	pred_zss_root: ZSSNode = ZSSNode.from_block(block=pred)
	ground_truth_zss_root: ZSSNode = ZSSNode.from_block(block=ground_truth)

	return {"TED": zss.simple_distance(pred_zss_root, ground_truth_zss_root)}

def path_based_similarities(pred: ParsedBlock, ground_truth: ParsedBlock) -> dict[str, float]:
	from itertools import takewhile, product

	def get_paths(block: ParsedBlock, curr_path: Optional[tuple[str]]=None) -> set[tuple[str]]:
		if curr_path is None:
			curr_path: tuple[str] = []
		path: tuple[str] = curr_path + [block.text]

		paths: set[tuple[str]] = {tuple(path)}

		if block.children is not None:
			for child in block.children:
				paths.update(get_paths(block=child, curr_path=path))
		
		return paths
	
	pred_paths: set[tuple[str]] = get_paths(pred)
	ground_truth_paths: set[tuple[str]] = get_paths(ground_truth)

	true_positives: set[tuple[str]] = pred_paths & ground_truth_paths
	tp: int = len(true_positives)
	false_positives: set[tuple[str]] = pred_paths - ground_truth_paths
	fp: int = len(false_positives)
	false_negatives: set[tuple[str]] = ground_truth_paths - pred_paths
	fn: int = len(false_negatives)
	# True negatives are not meaningful in the context

	accuracy: float = tp/len(ground_truth_paths) if len(ground_truth_paths) != 0 else 1.0
	precision: float = tp/(tp+fp) if (tp+fp) != 0 else 1.0
	recall: float = tp/(tp+fn) if (tp+fn) != 0 else 1.0
	f1: float = 2*precision*recall/(precision+recall) if (precision+recall) != 0 else 0.0
	
	def least_common_prefix(pred_path: tuple[str], ground_truth_path: tuple[str]) -> float:
		lcp: tuple[str] = [x for x, y in takewhile(lambda pair: pair[0] == pair[1], zip(pred_path, ground_truth_path))]

		return len(lcp)/len(ground_truth_path)
	
	def least_common_suffix(pred_path: tuple[str], ground_truth_path: tuple[str]) -> float:
		lcs: tuple[str] = [
			x for x, y in takewhile(lambda pair: pair[0] == pair[1], zip(pred_path[::-1], ground_truth_path[::-1]))
		]

		return len(lcs)/len(ground_truth_path)

	total_lcp: float = sum(least_common_prefix(x, y) for x, y in product(pred_paths, ground_truth_paths))
	total_lcs: float = sum(least_common_suffix(x, y) for x, y in product(pred_paths, ground_truth_paths))

	return {
		"Path accuracy": accuracy,
		"Path precision": precision,
		"Path recall": recall,
		"Path F1": f1,
		"Path LCP": total_lcp,
		"Path LCS": total_lcs
	}

def edge_based_similarities(pred: ParsedBlock, ground_truth: ParsedBlock) -> dict[str, float]:
	def get_edges(block: ParsedBlock) -> set[tuple[str, str]]:
		edges: set[tuple[str, str]] = set()

		if block.children is not None:
			for child in block.children:
				edges.add((block.text, child.text))
				edges.update(get_edges(block=child))
		
		return edges
	
	pred_edges: set[tuple[str, str]] = get_edges(pred)
	ground_truth_edges: set[tuple[str, str]] = get_edges(ground_truth)

	true_positives: set[tuple[str, str]] = pred_edges & ground_truth_edges
	tp: int = len(true_positives)
	false_positives: set[tuple[str, str]] = pred_edges - ground_truth_edges
	fp: int = len(false_positives)
	false_negatives: set[tuple[str, str]] = ground_truth_edges - pred_edges
	fn: int = len(false_negatives)
	# True negatives are not meaningful in the context

	accuracy: float = tp/len(ground_truth_edges) if len(ground_truth_edges) != 0 else 1.0
	precision: float = tp/(tp+fp) if (tp+fp) != 0 else 1.0
	recall: float = tp/(tp+fn) if (tp+fn) != 0 else 1.0
	f1: float = 2*precision*recall/(precision+recall) if (precision+recall) != 0 else 0.0
	
	return {
		"Edge accuracy": accuracy,
		"Edge precision": precision,
		"Edge recall": recall,
		"Edge F1": f1
	}

def line_level_metrics(pred: list[str], ground_truth: list[str]) -> dict[str, float]:
	pred: str[str] = set(pred)
	ground_truth: set[str] = set(ground_truth)

	intersection: set[str] = pred & ground_truth
	union: set[str] = pred | ground_truth

	precision: float = len(intersection)/len(ground_truth) if len(ground_truth) != 0 else 1.0
	recall: float = len(intersection)/len(pred) if len(pred) != 0 else 1.0
	jaccard: float = len(intersection)/len(union) if len(union) != 0 else 1.0

	return {
		"Line precision": precision,
		"Line recall": recall,
		"Line Jaccard": jaccard
	}

def word_level_metrics(pred: list[str], ground_truth: list[str]) -> dict[str, float]:
	matcher = difflib.SequenceMatcher(None, pred, ground_truth)
	ratios = []

	for tag, i1, i2, j1, j2 in matcher.get_opcodes():
		if tag == "equal":
			for pred_line, ground_truth_line in zip(pred[i1:i2], ground_truth[j1:j2]):
				pred_words: list[str] = pred_line.split()
				ground_truth_words: list[str] = ground_truth_line.split()
				if len(pred_words) != 0 or len(ground_truth_words) != 0:
					ratios.append(1.0 - difflib.SequenceMatcher(None, pred_words, ground_truth).ratio())
	
	avg_ratio: float = sum(ratios)/len(ratios) if len(ratios) != 0 else 1.0

	return {
		"Average word similarity ratio on matching lines": avg_ratio
	}

class ParsedBlock:
	def __init__(self, text: str):
		self.text: str = text
		self.children: Optional[list[ParsedBlock]] = None

	def add_child(self, child: ParsedBlock):
		if self.children is None:
			self.children = []
		self.children.append(child)

def parse_tree_from_lines(lines: list[str]) -> Optional[ParsedBlock]:
	root = ParsedBlock("ROOT")
	stack = [(root, -1)]

	for line in lines:
		stripped = line.lstrip('\t')
		depth = len(line) - len(stripped)
		node = ParsedBlock(stripped)

		while stack and stack[-1][1] >= depth:
			stack.pop()

		parent = stack[-1][0]
		parent.add_child(node)
		stack.append((node, depth))

	return root

def evaluation(test_dir: str, file_name: str) -> dict[str, dict[str, float]]:
	with open(f"{os.path.join(test_dir, file_name)}.txt", "r", encoding="utf-8", errors="replace") as f:
		pred_f = f.readlines()

	pred_root: ParsedBlock = parse_tree_from_lines(lines=pred_f)
	
	with open(f"{os.path.join(test_dir, 'ground_truths', file_name)}.txt", "r", encoding="utf-8", errors="replace") as f:
		ground_truth_f = f.readlines()

	ground_truth_root: ParsedBlock = parse_tree_from_lines(lines=ground_truth_f)

	return {
		"structural": {
			**tree_edit_distance(pred=pred_root, ground_truth=ground_truth_root),
			**path_based_similarities(pred=pred_root, ground_truth=ground_truth_root),
			**edge_based_similarities(pred=pred_root, ground_truth=ground_truth_root)
		},
		"content": {
			**line_level_metrics(pred=pred_f, ground_truth=ground_truth_f),
			**word_level_metrics(pred=pred_f, ground_truth=ground_truth_f)
		}
	}

if __name__ == "__main__":
	unfccc_test_file_names: list[str] = ["sample3.docx", "A6.4-PROC-ACCR-002.docx"]
	results: dict = {}
	for file_name in unfccc_test_file_names:
		results[file_name] = evaluation(test_dir="test/unfccc", file_name=file_name)

	print(results)
	