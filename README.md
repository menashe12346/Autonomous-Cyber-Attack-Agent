📦 Install dependencies:

Arch linux:

sudo pacman -Syu                                                       
sudo pacman -S base-devel cmake git

Ubunto:
 
sudo apt update
sudo apt install -y build-essential cmake git

📥 Download and Build llama.cpp

Arch linux:

git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
mkdir build
cd build
cmake ..
cmake --build . --config Release -j$(nproc)


 
