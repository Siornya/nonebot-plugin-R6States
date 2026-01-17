#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <unordered_map>
#include <vector>
#include <string>
#include <sstream>
#include <algorithm>

#include "player.hpp"

using namespace std;
namespace py = pybind11;

/*
使用unordered_map<string, vector<string> >对应sections: Dict[str, List[str]]
按固定规则分组、拼接字符串，最终返回一个可直接发送给 bot 的文本
*/
string format_overview(const unordered_map<string, vector<string> > &sections, bool full_mode) {
	Player player;
	unordered_map<string, vector<string> > contexts;

	auto clean_number = [](string s) {
		s.erase(remove(s.begin(), s.end(), ','), s.end());
		return s;
	};

	for (const auto &[section, texts]: sections) {
		vector<string> new_texts;

		if (section == "Current Season") {
			player.rank = texts[0];
			player.RP = stoi(clean_number(texts[1]));
			player.RP_p = texts[3];
			player.TRN_Elo = stoi(clean_number(texts[5]));
			player.TRN_Elo_p = texts[7];
			player.season_ranked_kd = stod(clean_number(texts[12]));
			player.season_ranked_win_rate = texts[13];

			new_texts.emplace_back(
				format("{} {}RP ({})\nTRN Elo:{} ({})\nPlaylist  KD   Win%\nRanked {} {}",
				       player.rank, player.RP, player.RP_p, player.TRN_Elo, player.TRN_Elo_p,
				       player.season_ranked_kd, player.season_ranked_win_rate));

			if (full_mode) {
				new_texts.emplace_back(
					format("Unranked {} {}\nQuick Match {} {}\nEvent {} {}",
					       texts[15], texts[16], texts[18], texts[19], texts[21], texts[22]));
			}
		} else if (section == "Season Peaks") {
			new_texts.emplace_back("SEASON     BEST   KD  MATCHES");

			size_t idx = 3;
			while (idx < texts.size() && texts[idx] != "SEASON") {
				new_texts.emplace_back(
					texts[idx] + ' ' + texts[idx + 1] + "RP " + texts[idx + 3] + ' ' + texts[idx + 4]);
				idx += 5;
			}

			new_texts.emplace_back("SEASON     BEST   KD  MATCHES");
			idx += 3;

			size_t pre5 = min(idx + 25, texts.size());
			while (idx < pre5) {
				new_texts.emplace_back(
					texts[idx] + ' ' + texts[idx + 1] + "RP " + texts[idx + 3] + ' ' + texts[idx + 4]);
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
					     pair{28, 31}, {31, 34}, {34, 37}, {37, 40}, {40, 42},
					     {42, 44}, {44, 46}, {46, 48}, {48, 50}, {50, 52}
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
