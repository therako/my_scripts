# alias
alias utcnow="date -u \"+%Y-%m-%dT%H:%M:%SZ\""
alias ipy='python -m IPython'
alias jn='jupyter notebook'
alias l='ls -l'
alias la='ls -a'
alias lla='ls -la'
alias lt='ls --tree'
eval $(thefuck --alias)


# Git
alias git-remove-untracked='git fetch --prune && git branch -r | awk "{print \$1}" | egrep -v -f /dev/fd/0 <(git branch -vv | grep origin) | awk "{print \$1}" | xargs git branch -D' 
alias git-safe-push='ggpush --force-with-lease'


# Docker
alias docker-stop-all='docker ps --format "table {{.Names}}" | xargs docker stop'


# Go
export PATH=$PATH:$HOME/go/bin
gocover () { 
    t="/tmp/go-cover.$$.tmp"
    go test -coverprofile=$t $@ && go tool cover -html=$t && unlink $t
}


# Workspace
WORKSPACE="$HOME/w"
alias w="cd ${WORKSPACE}"
export PATH="$PATH:$WORKSPACE/bin"
