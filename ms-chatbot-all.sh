#!/bin/bash

NB_TENANTS=12

start_all_chatbots() {

	#repeat NB_TENANTS times the call to script deploy.sh, with i as the tenant number as argument
	for ((i=0;i<$NB_TENANTS;i++)); do
    		nohup ./ms-chatbot.sh $i &
	done
	wait

}

stop_all_chatbots() {
	killall ms-chatbot.sh
}

case $1 in
    up)
        start_all_chatbots
        ;;
    down)
        stop_all_chatbots
        ;;
    *)
        echo "Usage: $0 {up|down}"
        exit 1
        ;;
esac
