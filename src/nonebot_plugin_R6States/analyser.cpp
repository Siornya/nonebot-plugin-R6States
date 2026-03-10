#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "player.hpp"

string analyse() {
	string result;
	return result;
}

PYBIND11_MODULE(analyser, m) {
	m.def(
		"analyse",
		&analyse
	);
}