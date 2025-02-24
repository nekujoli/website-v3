if [ $# -eq 0 ]
  then
    echo "syntax: $0 <comment for the commit, WITH QUOTES>"
fi
git add .
git commit -m "$1"
git push origin main
