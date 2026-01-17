#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <unordered_map>
#include <vector>
#include <string>
#include <sstream>
#include <algorithm>

using namespace std;
namespace py = pybind11;

/*
作用：
等价于 Python 的 format_overview 函数。
接收 sections: Dict[str, List[str]]，根据 section 名称和 full_mode，
按固定规则分组、拼接字符串，最终返回一个可直接发送给 bot 的文本。

实现要点：
- 严格保持 Python 版本的分支结构
- 使用  vector /  unordered_map 对应 Python list / dict
- 使用  ostringstream 高效拼接字符串
*/
string format_overview(const unordered_map<string, vector<string> > &sections, bool full_mode) {
	unordered_map<string, vector<string> > contexts;

	for (const auto &[section, texts]: sections) {
		vector<string> new_texts;

		if (section == "Current Season") {
			new_texts.emplace_back(
				accumulate(texts.begin(), texts.begin() + 4, string(),
				           [](const string &a, const string &b) {
					           return a.empty() ? b : a + " " + b;
				           })
			);

			new_texts.emplace_back(texts[4] + " " + texts[5] + " " + texts[7]);

			if (!full_mode) {
				for (int i = 8; i <= 13; i += 3) {
					new_texts.emplace_back(
						texts[i] + " " + texts[i + 1] + " " + texts[i + 2]
					);
				}
			} else {
				for (size_t idx = 8; idx < texts.size(); idx += 3) {
					ostringstream oss;
					for (size_t j = idx; j < min(idx + 3, texts.size()); ++j) {
						if (j > idx) oss << ' ';
						oss << texts[j];
					}
					new_texts.emplace_back(oss.str());
				}
			}
		} else if (section == "Season Peaks") {
			size_t idx = 3;

			new_texts.emplace_back(texts[0] + " " + texts[1] + " " + texts[2]);

			while (idx < texts.size() && texts[idx] != "SEASON") {
				ostringstream oss;
				for (size_t j = idx; j < idx + 5; ++j) {
					if (j > idx) oss << ' ';
					oss << texts[j];
				}
				new_texts.emplace_back(oss.str());
				idx += 5;
			}

			new_texts.emplace_back(texts[idx] + " " + texts[idx + 1] + " " + texts[idx + 2]);
			idx += 3;

			size_t pre5 = min(idx + 25, texts.size());
			while (idx < pre5) {
				ostringstream oss;
				for (size_t j = idx; j < idx + 5; ++j) {
					if (j > idx) oss << ' ';
					oss << texts[j];
				}
				new_texts.emplace_back(oss.str());
				idx += 5;
			}
		} else if (section == "Lifetime Overall") {
			for (auto [l, r]: {pair{0, 2}, {2, 4}, {6, 8}, {8, 10}, {10, 12}, {20, 22}}) {
				new_texts.emplace_back(texts[l] + " " + texts[l + 1]);
			}

			if (full_mode) {
				for (int idx = 12; idx < 20; idx += 2) {
					new_texts.emplace_back(texts[idx] + " " + texts[idx + 1]);
				}
			}
		} else if (section == "Lifetime Ranked" || section == "Lifetime Unranked + Quick Match") {
			const vector<pair<int, int> > fixed_groups = {{0, 2}, {2, 4}, {4, 6}, {14, 16}};

			for (auto [l, r]: fixed_groups) {
				new_texts.emplace_back(texts[l] + " " + texts[l + 1]);
			}

			if (full_mode) {
				for (int idx = 6; idx < 14; idx += 2) {
					new_texts.emplace_back(texts[idx] + " " + texts[idx + 1]);
				}
			}
		} else if (section == "All Matches") {
			ostringstream oss;
			for (size_t i = 2; i < texts.size(); ++i) {
				oss << texts[i];
			}
			new_texts.emplace_back(oss.str());
		} else {
			for (auto [l, r]: {pair{0, 1}, {1, 3}}) {
				ostringstream oss;
				for (int i = l; i < r; ++i) {
					if (i > l) oss << ' ';
					oss << texts[i];
				}
				new_texts.emplace_back(oss.str());
			}

			if (full_mode) {
				for (auto [l, r]: {pair{3, 5}, {5, 7}, {7, 9}}) {
					new_texts.emplace_back(texts[l] + " " + texts[l + 1]);
				}
			}

			for (auto [l, r]: {pair{12, 14}, {14, 16}, {18, 21}, {21, 24}, {24, 26}, {26, 28}}) {
				ostringstream oss;
				for (int i = l; i < r; ++i) {
					if (i > l) oss << ' ';
					oss << texts[i];
				}
				new_texts.emplace_back(oss.str());
			}

			if (full_mode) {
				for (auto [l, r]:
				     {
					     pair{28, 31}, {31, 34}, {34, 37}, {37, 40},
					     {40, 42}, {42, 44}, {44, 46}, {46, 48},
					     {48, 50}, {50, 52}
				     }) {
					ostringstream oss;
					for (int i = l; i < r; ++i) {
						if (i > l) oss << ' ';
						oss << texts[i];
					}
					new_texts.emplace_back(oss.str());
				}
			}
		}

		contexts.emplace(section, move(new_texts));
	}

	ostringstream result;
	for (const auto &[section, texts]: contexts) {
		result << "===== " << section << " =====\n";
		for (const auto &line: texts) {
			result << line << '\n';
		}
		result << '\n';
	}

	return result.str();
}

PYBIND11_MODULE(formatter, m) {
	m.def(
		"format_overview",
		&format_overview,
		pybind11::arg("sections"),
		pybind11::arg("full_mode"),
		"Format overview text"
	);
}