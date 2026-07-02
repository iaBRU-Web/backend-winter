#include <iostream>
#include <string>

int main(int argc, char** argv) {
    std::string payload = (argc > 1) ? argv[1] : "";
    std::cout << "UE_INSTR(\"" << payload << "\")" << std::endl;
    return 0;
}
