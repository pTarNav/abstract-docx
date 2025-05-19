from __future__ import annotations
from typing import Optional
from itertools import takewhile, product

from abstract_docx.main import AbstractDocx
from abstract_docx.views.document import Block

def tree_edit_distance(pred: AbstractDocx, ground_truth: AbstractDocx) -> dict[str, float]:
	"""
	Zhang-Shasha algorithm
	"""
	import zss
	class ZSSNode(zss.Node):
		def __init__(self, label, children):
			super().__init__(label=label, children=children)

		@classmethod
		def from_block(cls, block: Block) -> ZSSNode:
			return cls(
				label=block.id,
				children=[ZSSNode.from_block(block=child) for child in block.children] if block.children is not None else []
			)

	pred_zss_root: ZSSNode = ZSSNode.from_block(block=pred.document_root)
	ground_truth_zss_root: ZSSNode = ZSSNode.from_block(block=ground_truth.document_root)

	return {"TED": zss.simple_distance(pred_zss_root, ground_truth_zss_root)}

def path_based_similarities(pred: AbstractDocx, ground_truth: AbstractDocx) -> dict[str, float]:
	def get_paths(block: Block, curr_path: Optional[list[int]]=None) -> set[list[int]]:
		if curr_path is None:
			curr_path: list[int] = []
		path: list[int] = curr_path + [block.id]

		paths: set[list[int]] = set()

		if block.children is not None:
			for child in block.children:
				paths = get_paths(block=child, curr_path=path)
		else:
			paths.update(path)
		
		return paths
	
	pred_paths: set[list[int]] = get_paths(pred.document_root)
	ground_truth_paths: set[list[int]] = get_paths(ground_truth.document_root)

	true_positives: set[list[int]] = pred_paths & ground_truth_paths
	tp: int = len(true_positives)
	false_positives: set[list[int]] = pred_paths - ground_truth_paths
	fp: int = len(false_positives)
	false_negatives: set[list[int]] = ground_truth_paths - pred_paths
	fn: int = len(false_negatives)
	# True negatives are not meaningful in the context

	accuracy: float = tp/len(ground_truth_paths) if len(ground_truth_paths) != 0 else 1.0
	precision: float = tp/(tp+fp) if (tp+fp) != 0 else 1.0
	recall: float = tp/(tp+fn) if (tp+fn) != 0 else 1.0
	f1: float = 2*precision*recall/(precision+recall) if (precision+recall) != 0 else 0.0
	
	def least_common_prefix(pred_path: list[int], ground_truth_path: list[int]) -> float:
		lcp: list[int] = [x for x, y in takewhile(lambda pair: pair[0] == pair[1], zip(pred_path, ground_truth_path))]

		return len(lcp)/len(ground_truth_path)
	
	def least_common_suffix(pred_path: list[int], ground_truth_path: list[int]) -> float:
		lcs: list[int] = [
			x for x, y in takewhile(lambda pair: pair[0] == pair[1], zip(pred_path[::-1], ground_truth_path[::-1]))
		]

		return len(lcs)/len(ground_truth_path)

	total_lcp: float = sum(least_common_prefix(x, y) for x, y in product(pred_paths, ground_truth_paths))
	total_lcs: float = sum(least_common_suffix(x, y) for x, y in product(pred_paths, ground_truth_paths))

	return {
		"Accuracy": accuracy,
		"Precision": precision,
		"Recall": recall,
		"F1": f1,
		"LCP": total_lcp,
		"LCS": total_lcs
	}

def edge_matching_measures(pred: AbstractDocx, ground_truth: AbstractDocx) -> dict[str, float]:
	def get_edges(block: Block) -> set[tuple[int, int]]:
		edges: set[tuple[int, int]] = set()

		if block.children is not None:
			for child in block.children:
				edges.add((block.id, child.id))
				edges.update(get_edges(block=child))
		
		return edges
	
	pred_edges: set[tuple[int, int]] = get_edges(pred.document_root)
	ground_truth_edges: set[tuple[int, int]] = get_edges(ground_truth.document_root)

	true_positives: set[tuple[int, int]] = pred_edges & ground_truth_edges
	tp: int = len(true_positives)
	false_positives: set[tuple[int, int]] = pred_edges - ground_truth_edges
	fp: int = len(false_positives)
	false_negatives: set[tuple[int, int]] = ground_truth_edges - pred_edges
	fn: int = len(false_negatives)
	# True negatives are not meaningful in the context

	accuracy: float = tp/len(ground_truth_edges) if len(ground_truth_edges) != 0 else 1.0
	precision: float = tp/(tp+fp) if (tp+fp) != 0 else 1.0
	recall: float = tp/(tp+fn) if (tp+fn) != 0 else 1.0
	f1: float = 2*precision*recall/(precision+recall) if (precision+recall) != 0 else 0.0
	
	return {
		"Accuracy": accuracy,
		"Precision": precision,
		"Recall": recall,
		"F1": f1
	}
