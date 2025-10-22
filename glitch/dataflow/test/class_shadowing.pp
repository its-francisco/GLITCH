$_user_home = "1234"

if ( ! defined( File["${_user_home}/.ssh"] ) ) {
  a =  $_user_home 
} else {
  a = $_user_home
}


