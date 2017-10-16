#!/bin/bash
#
CONFIG=/boot/config.txt
FUN="$1"
args=("$@")
ASK_TO_REBOOT=0
BLACKLIST=/etc/modprobe.d/raspi-blacklist.conf

if [ -z $FUN ]; then
    echo "Pick one of the functions"
    exit 1
fi

set_config_var() {
  lua - "$1" "$2" "$3" <<EOF > "$3.bak"
local key=assert(arg[1])
local value=assert(arg[2])
local fn=assert(arg[3])
local file=assert(io.open(fn))
local made_change=false
for line in file:lines() do
  if line:match("^#?%s*"..key.."=.*$") then
    line=key.."="..value
    made_change=true
  end
  print(line)
end

if not made_change then
  print(key.."="..value)
end
EOF
mv "$3.bak" "$3"
}
get_config_var() {
  lua - "$1" "$2" <<EOF
local key=assert(arg[1])
local fn=assert(arg[2])
local file=assert(io.open(fn))
for line in file:lines() do
  local val = line:match("^#?%s*"..key.."=(.*)$")
  if (val ~= nil) then
    print(val)
    break
  end
end
EOF
}


disable_raspi_config_at_boot() {
  if [ -e /etc/profile.d/raspi-config.sh ]; then
    rm -f /etc/profile.d/raspi-config.sh
    sed -i /etc/inittab \
      -e "s/^#\(.*\)#\s*RPICFG_TO_ENABLE\s*/\1/" \
      -e "/#\s*RPICFG_TO_DISABLE/d"
    telinit q
  fi
}

disable_boot_to_scratch() {
  if [ -e /etc/profile.d/boottoscratch.sh ]; then
    rm -f /etc/profile.d/boottoscratch.sh
    sed -i /etc/inittab \
      -e "s/^#\(.*\)#\s*BTS_TO_ENABLE\s*/\1/" \
      -e "/#\s*BTS_TO_DISABLE/d"
    telinit q
  fi
}

do_boot_behaviour() {
    BOOTOPT=${args[1]}
    echo "$BOOTOPT"
    case "$BOOTOPT" in
      Console)
        [ -e /etc/init.d/lightdm ] && update-rc.d lightdm disable 2
        disable_boot_to_scratch
        ;;
      Desktop)
        if [ -e /etc/init.d/lightdm ]; then
          if id -u pi > /dev/null 2>&1; then
            update-rc.d lightdm enable 2
            sed /etc/lightdm/lightdm.conf -i -e "s/^#autologin-user=.*/autologin-user=pi/"
            disable_boot_to_scratch
            disable_raspi_config_at_boot
          else
            echo "The pi user has been removed, can't set up boot to desktop"
          fi
        else
          echo "Do sudo apt-get install lightdm to allow configuration of boot to desktop"
          return 1
        fi
        ;;
      Scratch)
        if [ -e /usr/bin/scratch ]; then
          if id -u pi > /dev/null 2>&1; then
            [ -e /etc/init.d/lightdm ] && update-rc.d lightdm disable 2
            disable_raspi_config_at_boot
            enable_boot_to_scratch
          else
            echo "The pi user has been removed, can't set up boot to scratch"
          fi
        else
          echo "Do sudo apt-get install scratch to allow configuration of boot to scratch"
        fi
        ;;
      *)
        echo "Programmer error, unrecognised boot option"
        return 1
        ;;
    esac
    ASK_TO_REBOOT=1
}


get_timezone(){
    cat /etc/timezone
}

do_timezone(){
    timezone=${args[1]}
    if [ -z "$timezone" ]; then
        echo 'missing timezone'
        return 1
	fi
    echo "$timezone" | sudo tee /etc/timezone
    dpkg-reconfigure -f noninteractive tzdata
}


# $1 is 0 to disable camera, 1 to enable it
set_camera() {
  # Stop if /boot is not a mountpoint
  if ! mountpoint -q /boot; then
    return 1
  fi

  [ -e $CONFIG ] || touch $CONFIG

  if [ "$1" -eq 0 ]; then # disable camera
    set_config_var start_x 0 $CONFIG
    sed $CONFIG -i -e "s/^startx/#startx/"
    sed $CONFIG -i -e "s/^start_file/#start_file/"
    sed $CONFIG -i -e "s/^fixup_file/#fixup_file/"
  else # enable camera
    set_config_var start_x 1 $CONFIG
    CUR_GPU_MEM=$(get_config_var gpu_mem $CONFIG)
    if [ -z "$CUR_GPU_MEM" ] || [ "$CUR_GPU_MEM" -lt 128 ]; then
      set_config_var gpu_mem 128 $CONFIG
    fi
    sed $CONFIG -i -e "s/^startx/#startx/"
    sed $CONFIG -i -e "s/^fixup_file/#fixup_file/"
  fi
}

do_camera() {
  if [ ! -e /boot/start_x.elf ]; then
    echo "Your firmware appears to be out of date (no start_x.elf). Please update"
    return 1
  fi
  RET=${args[1]}
  if [ $RET -eq 0 ] || [ $RET -eq 1 ]; then
    ASK_TO_REBOOT=1
    set_camera $RET;
  else
    return 1
  fi
}

do_overclock() {
    OVERCLOCK=${args[1]}
    case "$OVERCLOCK" in
      None)
        set_overclock None 700 250 400 0
        ;;
      Modest)
        set_overclock Modest 800 250 400 0
        ;;
      Medium)
        set_overclock Medium 900 250 450 2
        ;;
      High)
        set_overclock High 950 250 450 6
        ;;
      Turbo)
        set_overclock Turbo 1000 500 600 6
        ;;
      Pi2)
        set_overclock Pi2 1000 500 500 2
        ;;
      *)
        echo "Programmer error, unrecognised overclock preset"
        return 1
        ;;
    esac
    ASK_TO_REBOOT=1

}

set_overclock() {
  set_config_var arm_freq $2 $CONFIG &&
  set_config_var core_freq $3 $CONFIG &&
  set_config_var sdram_freq $4 $CONFIG &&
  set_config_var over_voltage $5 $CONFIG &&
  echo "Set overclock to preset '$1'"
}

do_memory_split() { # Memory Split
  if [ -e /boot/start_cd.elf ]; then
    # New-style memory split setting
    if ! mountpoint -q /boot; then
      return 1
    fi
    ## get current memory split from /boot/config.txt
    CUR_GPU_MEM=$(get_config_var gpu_mem $CONFIG)
    [ -z "$CUR_GPU_MEM" ] && CUR_GPU_MEM=64
    ## ask users what gpu_mem they want
    NEW_GPU_MEM=${args[1]}
    set_config_var gpu_mem "$NEW_GPU_MEM" $CONFIG
    ASK_TO_REBOOT=1
  else # Old firmware so do start.elf renaming
    MEMSPLIT=$((256-args[1]))

    set_memory_split ${MEMSPLIT}
    ASK_TO_REBOOT=1

  fi
}

get_current_memory_split() {
  # Stop if /boot is not a mountpoint
  if ! mountpoint -q /boot; then
    return 1
  fi
  AVAILABLE_SPLITS="128 192 224 240"
  MEMSPLIT_DESCRIPTION=""
  for SPLIT in $AVAILABLE_SPLITS;do
    if [ -e /boot/arm${SPLIT}_start.elf ] && cmp /boot/arm${SPLIT}_start.elf /boot/start.elf >/dev/null 2>&1;then
      CURRENT_MEMSPLIT=$SPLIT
      MEMSPLIT_DESCRIPTION="${CURRENT_MEMSPLIT}"
      break
    fi
  done
}

set_memory_split() {
  cp -a /boot/arm${1}_start.elf /boot/start.elf
  sync
}

do_change_hostname() {
    NEW_HOSTNAME=${args[1]}
    echo $NEW_HOSTNAME > /etc/hostname
    sed -i "s/127.0.1.1.*$CURRENT_HOSTNAME/127.0.1.1\t$NEW_HOSTNAME/g" /etc/hosts
    ASK_TO_REBOOT=1
}
# $1 is 0 to enable overscan, 1 to disable it
set_overscan() {
  # Stop if /boot is not a mountpoint
  if ! mountpoint -q /boot; then
    return 1
  fi

  [ -e $CONFIG ] || touch $CONFIG

  if [ "$1" -eq 0 ]; then # disable overscan
    sed $CONFIG -i -e "s/^overscan_/#overscan_/"
    set_config_var disable_overscan 1 $CONFIG
  else # enable overscan
    set_config_var disable_overscan 0 $CONFIG
  fi
}
get_memory_split(){
  if [ -e /boot/start_cd.elf ]; then
    # New-style memory split setting
    if ! mountpoint -q /boot; then
      return 1
    fi
    ## get current memory split from /boot/config.txt
    CUR_GPU_MEM=$(get_config_var gpu_mem $CONFIG)
    [ -z "$CUR_GPU_MEM" ] && CUR_GPU_MEM=64
    echo "${CUR_GPU_MEM}"
  else # Old firmware so do start.elf renaming
    get_current_memory_split
    echo "${MEMSPLIT_DESCRIPTION}"
  fi
}
do_overscan() {
  RET=${args[1]}
  if [ $RET -eq 0 ] || [ $RET -eq 1 ]; then
    ASK_TO_REBOOT=1
    set_overscan $RET;
  else
    return 1
  fi
}
do_ssh() {
  if [ -e /var/log/regen_ssh_keys.log ] && ! grep -q "^finished" /var/log/regen_ssh_keys.log; then
    echo "Initial ssh key generation still running. Please wait and try again."
    return 1
  fi
  RET=${args[1]}
  if [ $RET -eq 0 ]; then
    update-rc.d ssh enable &&
    invoke-rc.d ssh start
  elif [ $RET -eq 1 ]; then
    update-rc.d ssh disable
  else
    return $RET
  fi
}
do_devicetree() {
  CURRENT_SETTING="enabled" # assume not disabled
  DEFAULT=
  if [ -e $CONFIG ] && grep -q "^device_tree=$" $CONFIG; then
    CURRENT_SETTING="disabled"
    DEFAULT=--defaultno
  fi
  RET=${args[1]}
  if [ $RET -eq 0 ]; then
    sed $CONFIG -i -e "s/^\(device_tree=\)$/#\1/"
    sed $CONFIG -i -e "s/^#\(device_tree=.\)/\1/"
    SETTING=enabled
  elif [ $RET -eq 1 ]; then
    sed $CONFIG -i -e "s/^#\(device_tree=\)$/\1/"
    sed $CONFIG -i -e "s/^\(device_tree=.\)/#\1/"
    if ! grep -q "^device_tree=$" $CONFIG; then
      printf "device_tree=\n" >> $CONFIG
    fi
    SETTING=disabled
  else
    return 0
  fi
  TENSE=is
  REBOOT=
  if [ $SETTING != $CURRENT_SETTING ]; then
    TENSE="will be"
    REBOOT=" after a reboot"
    ASK_TO_REBOOT=1
  fi
  
}
get_devicetree() {
  CURRENT_SETTING="1" # assume not disabled
  if [ -e $CONFIG ] && grep -q "^device_tree=$" $CONFIG; then
    CURRENT_SETTING="0"
  fi
  echo "${CURRENT_SETTING}"
}

#arg[1] enable I2C 1/0 arg[2] load by default 1/0
#again 0 enable 1 disable
do_i2c() {
  DEVICE_TREE="yes" # assume not disabled
  DEFAULT=
  if [ -e $CONFIG ] && grep -q "^device_tree=$" $CONFIG; then
    DEVICE_TREE="no"
  fi

  CURRENT_SETTING="off" # assume disabled
  DEFAULT=--defaultno
  if [ -e $CONFIG ] && grep -q -E "^(device_tree_param|dtparam)=([^,]*,)*i2c(_arm)?(=(on|true|yes|1))?(,.*)?$" $CONFIG; then
    CURRENT_SETTING="on"
    DEFAULT=
  fi

  if [ $DEVICE_TREE = "yes" ]; then
    #First arg: "Would you like the ARM I2C interface to be enabled?" 
    RET=${args[1]}
    [ -z "$RET" ] && exit 1
    if [ $RET -eq 0 ]; then
      SETTING=on
      STATUS=enabled
    elif [ $RET -eq 1 ]; then
      SETTING=off
      STATUS=disabled
    else
      return 0
    fi
    TENSE=is
    REBOOT=
    if [ $SETTING != $CURRENT_SETTING ]; then
      TENSE="will be"
      REBOOT=" after a reboot"
      ASK_TO_REBOOT=1
    fi
    sed $CONFIG -i -r -e "s/^((device_tree_param|dtparam)=([^,]*,)*i2c(_arm)?)(=[^,]*)?/\1=$SETTING/"
    if ! grep -q -E "^(device_tree_param|dtparam)=([^,]*,)*i2c(_arm)?=[^,]*" $CONFIG; then
      printf "dtparam=i2c_arm=$SETTING\n" >> $CONFIG
    fi
    if [ $SETTING = "off" ]; then
      return 0
    fi
  fi

  CURRENT_STATUS="yes" # assume not blacklisted
  DEFAULT=
  if [ -e $BLACKLIST ] && grep -q "^blacklist[[:space:]]*i2c[-_]bcm2708" $BLACKLIST; then
    CURRENT_STATUS="no"
    DEFAULT=--defaultno
  fi

  if ! [ -e $BLACKLIST ]; then
    touch $BLACKLIST
  fi

  #Second Param: "Would you like the I2C kernel module to be loaded by default?" $DEFAULT 20 60 2
  RET=${args[2]}
  [ -z "$RET" ] && RET=RET=${args[1]}
  if [ $RET -eq 0 ]; then
    sed $BLACKLIST -i -e "s/^\(blacklist[[:space:]]*i2c[-_]bcm2708\)/#\1/"
    sed $BLACKLIST -i -e "s/^\(blacklist[[:space:]]*i2c-dev\)/#\1/"
    modprobe i2c-bcm2708
    modprobe i2c-dev
  elif [ $RET -eq 1 ]; then
    sed $BLACKLIST -i -e "s/^#\(blacklist[[:space:]]*i2c[-_]bcm2708\)/\1/"
    sed $BLACKLIST -i -e "s/^#\(blacklist[[:space:]]*i2c-dev\)/\1/"
    if ! grep -q "^blacklist i2c[-_]bcm2708" $BLACKLIST; then
      printf "blacklist i2c-bcm2708\n" >> $BLACKLIST
    fi
    if ! grep -q "^blacklist i2c-dev" $BLACKLIST; then
      printf "blacklist i2c-bcm2708\n" >> $BLACKLIST
    fi
  else
    return 0
  fi

  exit
}

get_i2c() {
  if grep -q -E "^(device_tree_param|dtparam)=([^,]*,)*i2c(_arm)?(=(on|true|yes|1))?(,.*)?$" $CONFIG; then
    echo 0
  else
    echo 1
  fi
}


#arg[1] enable SPI 1/0 arg[2] load by default 1/0
#again 0 enable 1 disable
do_spi() {
  DEVICE_TREE="yes" # assume not disabled
  DEFAULT=
  if [ -e $CONFIG ] && grep -q "^device_tree=$" $CONFIG; then
    DEVICE_TREE="no"
  fi

  CURRENT_SETTING="off" # assume disabled
  DEFAULT=--defaultno
  if [ -e $CONFIG ] && grep -q -E "^(device_tree_param|dtparam)=([^,]*,)*spi(=(on|true|yes|1))?(,.*)?$" $CONFIG; then
    CURRENT_SETTING="on"
    DEFAULT=
  fi

  if [ $DEVICE_TREE = "yes" ]; then
    #Param1 "Would you like the SPI interface to be enabled?"
    RET=${args[1]}
    [ -z "$RET" ] && exit 1
    if [ $RET -eq 0 ]; then
      SETTING=on
      STATUS=enabled
    elif [ $RET -eq 1 ]; then
      SETTING=off
      STATUS=disabled
    else
      return 0
    fi
    TENSE=is
    REBOOT=
    if [ $SETTING != $CURRENT_SETTING ]; then
      TENSE="will be"
      REBOOT=" after a reboot"
      ASK_TO_REBOOT=1
    fi
    sed $CONFIG -i -r -e "s/^((device_tree_param|dtparam)=([^,]*,)*spi)(=[^,]*)?/\1=$SETTING/"
    if ! grep -q -E "^(device_tree_param|dtparam)=([^,]*,)*spi=[^,]*" $CONFIG; then
      printf "dtparam=spi=$SETTING\n" >> $CONFIG
    fi

    if [ $SETTING = "off" ]; then
      return 0
    fi
  fi

  CURRENT_STATUS="yes" # assume not blacklisted
  DEFAULT=
  if [ -e $BLACKLIST ] && grep -q "^blacklist[[:space:]]*spi[-_]bcm2708" $BLACKLIST; then
    CURRENT_STATUS="no"
    DEFAULT=--defaultno
  fi

  if ! [ -e $BLACKLIST ]; then
    touch $BLACKLIST
  fi

  #Param2 "Would you like the SPI kernel module to be loaded by default?"
  RET=${args[2]}
  [ -z "$RET" ] && RET=${args[1]}
  if [ $RET -eq 0 ]; then
    sed $BLACKLIST -i -e "s/^\(blacklist[[:space:]]*spi[-_]bcm2708\)/#\1/"
    modprobe spi-bcm2708
  elif [ $RET -eq 1 ]; then
    sed $BLACKLIST -i -e "s/^#\(blacklist[[:space:]]*spi[-_]bcm2708\)/\1/"
    if ! grep -q "^blacklist spi[-_]bcm2708" $BLACKLIST; then
      printf "blacklist spi-bcm2708\n" >> $BLACKLIST
    fi
  else
    return 0
  fi
}

get_spi() {
  if grep -q -E "^(device_tree_param|dtparam)=([^,]*,)*spi(=(on|true|yes|1))?(,.*)?$" $CONFIG; then
    echo 0
  else
    echo 1
  fi
}

do_serial() {
  CURRENT_STATUS="yes" # assume ttyAMA0 output enabled
  if ! grep -q "^T.*:.*:respawn:.*ttyAMA0" /etc/inittab; then
    CURRENT_STATUS="no"
  fi

  #"Would you like a login shell to be accessible over serial?"
  RET=${args[1]}
  if [ $RET -eq 1 ]; then
    sed -i /etc/inittab -e "s|^.*:.*:respawn:.*ttyAMA0|#&|"
    sed -i /boot/cmdline.txt -e "s/console=ttyAMA0,[0-9]\+ //"
    #"Serial is now disabled" 
  elif [ $RET -eq 0 ]; then
    sed -i /etc/inittab -e "s|^#\(.*:.*:respawn:.*ttyAMA0\)|\1|"
    if ! grep -q "^T.*:.*:respawn:.*ttyAMA0" /etc/inittab; then
      printf "T0:23:respawn:/sbin/getty -L ttyAMA0 115200 vt100\n" >> /etc/inittab
    fi
    if ! grep -q "console=ttyAMA0" /boot/cmdline.txt; then
      sed -i /boot/cmdline.txt -e "s/root=/console=ttyAMA0,115200 root=/"
    fi
    #"Serial is now enabled"
  else
    return $RET
  fi
}

#"0" "Auto","1" "Force 3.5mm ('headphone') jack","2" "Force HDMI"
do_audio() {
  AUDIO_OUT=${args[1]}
  amixer cset numid=3 "$AUDIO_OUT"
}

get_camera() {
    OUTPUT="$(vcgencmd get_camera)"
    echo $OUTPUT
}

get_serial() {
    if ! grep -q "^T.*:.*:respawn:.*ttyAMA0" /etc/inittab; then
        echo 0
        return 0
    fi
    echo 1
    return 0
}
get_w1(){
    output=$( cat $CONFIG | grep ' *dtoverlay*=*w1-gpio' )
    if [ -z "$output" ]; then
        echo 0
    else
        echo 1
    fi
    return 0
}
do_w1(){
    RET=${args[1]}
    CURRENT=$(get_w1)
    if [ $RET -eq 1 -a $CURRENT -eq 0 ]; then  
        output=$( cat $CONFIG | grep w1-gpio )
        if [ -z "$output" ]; then
            echo "dtoverlay=w1-gpio" >> $CONFIG
        else
            sed  -i "s/\(#dtoverlay.*=.*w1-gpio\).*/\dtoverlay=w1-gpio/" $CONFIG
        fi
        ASK_TO_REBOOT=1
    elif [ $RET -eq 0 -a $CURRENT -eq 1 ]; then
        sed  -i "/\(dtoverlay.*=.*w1-gpio\).*/d" $CONFIG
        ASK_TO_REBOOT=1
    fi
    return 0
}

case "$FUN" in
  1) do_boot_behaviour ;;
  2) do_camera ;;
  3) do_overclock ;;
  4) do_change_hostname ;;
  5) do_overscan ;;
  6) do_memory_split ;;
  7) get_memory_split ;;
  8) do_ssh ;;
  9) do_devicetree ;;
  10) get_devicetree ;;
  11) do_i2c ;;
  12) do_spi ;;
  13) do_serial ;;
  14) do_audio ;;
  15) get_timezone ;;
  16) do_timezone ;;
  17) get_camera ;;
  18) get_serial ;;
  19) do_w1 ;;
  20) get_w1 ;;
  21) get_i2c ;;
  22) get_spi ;;
  *) echo 'N/A' && exit 1;;
 esac || echo "There was an error running option $FUN" 
if [ $ASK_TO_REBOOT = 1 ]; then
    echo 'reboot required';
fi