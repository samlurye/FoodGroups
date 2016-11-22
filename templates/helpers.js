function submitSurvey(pref1) {

	var config = {
                apiKey: "AIzaSyBxrm_AcfuQCMVWCFwut4ujjKIEqoPzXwQ",
                authDomain: "foodgroups-c09d1.firebaseapp.com",
                databaseURL: "https://foodgroups-c09d1.firebaseio.com",
                storageBucket: "",
                messagingSenderId: "522334661408"
            };
            firebase.initializeApp(config);
            
	var postData {
		pref1: pref1
	};

	var newPostKey = firebase.database().ref().child('posts').push().key

	var updates = {};
	updates['/surveys/' + newPostKey] = postData;
	//updates['/user-posts/' + uid + '/' + newPostKey] = postData;
	
	return firebase.database().ref().update(updates);
}