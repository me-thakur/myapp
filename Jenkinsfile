pipeline {
    agent any

    stages {

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t myapp:jenkins-test .'
            }
        }

        stage('Run Application') {
            steps {
                sh 'docker rm -f myapp-jenkins-test 2>/dev/null || true'
                sh 'docker run -d --name myapp-jenkins-test --network devops-net -p 8082:8080 myapp:jenkins-test'
            }
        }

    }
}
