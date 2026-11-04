#include "../sampler/liasampler.h"

struct my_args {
    std::string smtFilePath;
    std::string outputDir{getcwd(NULL, 0)};
    size_t maxNumSamples = 1000;
    double maxTimeLimit = 3600.0;
    int randomSeed = 0;
};

void printHelp(const char* programName) {
    std::cout << "Usage: " << programName << " [options]\n";
    std::cout << "Options:\n";
    std::cout << "  -i <smt file>               Specify the path to the input file\n";
    std::cout << "  -o <output dir>             Specify the output directory path\n";
    std::cout << "  -n <num samples>            Specify the number of samples\n";
    std::cout << "  -t <time limit>             Set the time limit (in seconds)\n";
    std::cout << "  -s <seed>                   Set the random seed\n";
    std::cout << "  -h                          Display this help message\n";
}

bool parseOpt(my_args* argp, int argc, char* argv[]) {
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "-h") {
            printHelp(argv[0]);
            return false;
        } else if (arg == "-i") {
            if (i + 1 < argc)
                argp->smtFilePath = argv[++i];
            else {
                std::cerr << "Please enter a smt file." << std::endl;
                return false;
            }
        } else if (arg == "-o") {
            if (i + 1 < argc)
                argp->outputDir = argv[++i];
            else {
                std::cerr << "Please enter an output directory." << std::endl;
                return false;
            }
        } else if (arg == "-n") {
            if (i + 1 < argc)
                argp->maxNumSamples = atoll(argv[++i]);
            else {
                std::cerr << "Please specify the number of samples." << std::endl;
                return false;
            }
        } else if (arg == "-t") {
            if (i + 1 < argc)
                argp->maxTimeLimit = atof(argv[++i]);
            else {
                std::cerr << "Please specify a time limit." << std::endl;
                return false;
            }
        } else if (arg == "-s") {
            if (i + 1 < argc)
                argp->randomSeed = atoi(argv[++i]);
            else {
                std::cerr << "Please enter a seed value." << std::endl;
                return false;
            }
        } else {
            std::cerr << "Unknown argument: " << arg << std::endl;
            return false;
        }
    }
    return true;
}

int main(int argc, char* argv[]) {
    // Z3_enable_trace("solve_eqs_round");
    // Z3_enable_trace("solve_eqs_subst");
    // Z3_enable_trace("solve_eqs");
    Z3_enable_trace("sampling_init");
    Z3_enable_trace("sampler");

    if (argc == 1) {
        printHelp(argv[0]);
        return 1;
    }

    my_args arg;
    bool parseRes = parseOpt(&arg, argc, argv);
    if (!parseRes) {
        return 1;
    }

    z3::context ctx;
    sampler::LiaSampler mySampler(&ctx , arg.smtFilePath, arg.outputDir, arg.maxNumSamples, arg.maxTimeLimit, arg.randomSeed);

    try {
        mySampler.sampling();
    } catch (const std::exception& error) {
        std::cerr << "Sampling failed: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
