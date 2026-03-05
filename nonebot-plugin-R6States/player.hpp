#ifndef NONEBOT_PLUGIN_R6TRACKERAPI_PLAYER_HPP
#define NONEBOT_PLUGIN_R6TRACKERAPI_PLAYER_HPP
#include <string>

using std::string;

struct Player {
	// Current Season
	string rank;
	int RP;
	string RP_p;
	int TRN_Elo;
	string TRN_Elo_p;
	int Level;
	double season_ranked_kd;
	string season_ranked_win_rate;
	// Lifetime Overall
	double lifetime_overall_win_rate;
	double lifetime_overall_kd;
	double lifetime_overall_hs;
	double lifetime_overall_kpm;
	int lifetime_overall_abandons;
	// Lifetime Ranked
	double lifetime_ranked_win_rate;
	double lifetime_ranked_kd;
	double lifetime_ranked_kpm;
	int lifetime_ranked_abandons;
	// Season Overview
	int season_matches_played;
	int season_ranked_matches_played;
	int season_unranked_matches_played;
	int season_quickmatch_matches_played;
	int season_event_matches_played;
	int season_ranked_wins;
	int season_ranked_losses;
	double season_ranked_kda;
	double season_ranked_hs;
	double season_ranked_matches_played_p;
	double season_ranked_matches_losses_p;
	int season_ranked_kills;
	double season_ranked_kills_p;
	int season_ranked_deaths;
	double season_ranked_deaths_p;
	int season_ranked_aces;
	double season_ranked_clutches_win;
	int season_ranked_clutches_won;
	int season_ranked_clutches_1v5;
	double season_ranked_esr;
	int season_ranked_abandons;
};


#endif //NONEBOT_PLUGIN_R6TRACKERAPI_PLAYER_HPP