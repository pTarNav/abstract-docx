from utils.validation.hierarchy import tree_edit_distance, path_based_similarities, edge_matching_measures
from abstract_docx.main import AbstractDocx
from abstract_docx.views.document import Block, Paragraph
import json

if __name__ == "__main__":
	paths = [
		"test/unfccc/A6.4-PROC-ACCR-002.docx",
		"test/unfccc/SB007_report.docx"
	]

	def load_ground_truth(x) -> Block:
		raw_children = x.get("children")
		if raw_children is not None:
			children = [load_ground_truth(child) for child in x["children"]]
		else:
			children = None

		return Block(id=x["id"], children=children)
	
	results: dict = {}
	for path in paths:
		with open(f"{path}.json", "r", encoding="utf-8") as f:
			raw_docx_json = json.load(f)
		
		ground_truth_document_root: Block = load_ground_truth(raw_docx_json)
		
		pred = AbstractDocx.read(file_path=path)
		pred()

		ground_truth = pred.model_copy(deep=True)
		ground_truth._document_root = ground_truth_document_root

		results[path] = tree_edit_distance(pred=pred, ground_truth=ground_truth)
		results[path].update(path_based_similarities(pred=pred, ground_truth=ground_truth))
		results[path].update(edge_matching_measures(pred=pred, ground_truth=ground_truth))
	
	print(results)