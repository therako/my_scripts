#!/bin/bash

/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
brew install brew-cask
# homebrew taps
brew tap caskroom/cask
brew tap caskroom/versions
brew tap homebrew/boneyard
brew tap caskroom/fonts
brew bundle


# Vim
unlink /usr/local/bin/vim
ln -s /usr/local/bin/gvim /usr/local/bin/vim
git clone https://github.com/VundleVim/Vundle.vim.git ~/.vim/bundle/Vundle.vim
wget https://gist.githubusercontent.com/therako/6646a67635477f626cd1b7c58c39adb6/raw/251ef41a1ce0e88b47b4f372edfb911b87db140f/.vimrc
mv .vimrc ~/.vimrc
vim +PluginInstall +qall


# oh-my-zsh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"
wget https://raw.githubusercontent.com/oskarkrawczyk/honukai-iterm/master/honukai.zsh-theme
mv -f honukai.zsh-theme  $HOME/.oh-my-zsh/themes/honukai.zsh-theme
chsh -s /bin/zsh

